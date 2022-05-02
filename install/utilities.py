import os
import site
import time
import yaml
import subprocess
from importlib import reload
from argparse import ArgumentParser

# need to have password sans cloudlab.pem copied to scheduler
# sudo ssh-keygen -p -N "" -f ./cloudlab.pem

#TODO: add namespace param to all kubectl commands


def import_or_install(package):
    try:
        __import__(package)
    except ImportError:
        import pip
        pip.main(['install', package])
    finally:
        reload(site)


def check_pod_status(label, namespace):
    from kubernetes import client, config

    config.load_kube_config()
    v1 = client.CoreV1Api()
    names = []
    pods_list = v1.list_namespaced_pod(
        namespace, label_selector=label, watch=False)
    for pod in pods_list.items:
        names.append(pod.metadata.name)

    if not names:
        return False

    for i in names:
        pod = v1.read_namespaced_pod_status(i, namespace, pretty='true')
        status = pod.status.phase
        if status != "Running":
            return False
    return True


def get_pod_names(namespace):
    from kubernetes import client, config

    label = "app=cerebro-controller"
    config.load_kube_config()
    v1 = client.CoreV1Api()
    pods_list = v1.list_namespaced_pod(
        namespace, label_selector=label, watch=False)
    controller = pods_list.items[0].metadata.name

    label = "type=cerebro-worker"
    pods_list = v1.list_namespaced_pod(
        namespace, label_selector=label, watch=False)
    workers = [i.metadata.name for i in pods_list.items]

    return [controller] + workers


class CerebroInstaller:
    def __init__(self, root_path, workers, kube_params):
        self.w = workers
        self.root_path = root_path

        self.kube_namespace = kube_params["kube_namespace"]
        self.cerebro_checkpoint_hostpath = kube_params["cerebro_checkpoint_hostpath"]
        self.cerebro_config_hostpath = kube_params["cerebro_config_hostpath"]
        self.cerebro_data_hostpath = kube_params["cerebro_data_hostpath"]
        self.cerebro_worker_data_hostpath = kube_params["cerebro_worker_data_hostpath"]

        self.s = None
        self.conn = None
        self.username = None

    def runbg(self, cmd, sockname="dtach"):
        return self.conn.run('dtach -n `mktemp -u /tmp/%s.XXXX` %s' % (sockname, cmd))

    def init_fabric(self):
        from fabric2 import ThreadingGroup, Connection

        workers = ["node"+str(i) for i in range(1, self.w+1)]
        host = "node0"

        self.username = subprocess.run(
            "whoami", capture_output=True, text=True).stdout.strip("\n")
        self.root_path = self.root_path.format(self.username)

        #initialize fabric
        user = self.username
        pem_path = "/users/{}/cloudlab.pem".format(self.username)
        connect_kwargs = {"key_filename": pem_path}
        self.conn = Connection(host, user=user, connect_kwargs=connect_kwargs)
        self.s = ThreadingGroup(*workers, user=user,
                                connect_kwargs=connect_kwargs)

    def init(self):
        subprocess.call(["sudo", "apt", "update"])
        subprocess.call(["sudo", "apt", "install", "-y", "python3-pip"])
        self.username = subprocess.run(
            "whoami", capture_output=True, text=True).stdout.strip("\n")
        self.root_path = self.root_path.format(self.username)

        import_or_install("fabric2")
        import_or_install("dask[complete]")
        subprocess.call(
            ["bash", "{}/install/init_cluster/path.sh".format(self.root_path)])

        self.init_fabric()

        self.s.run("whoami")
        self.s.run("rm -rf /users/{}/etl-wip".format(self.username))
        self.s.run(
            "git clone https://github.com/prsridha/etl-wip.git --branch kubernetes")

    def kubernetes_preinstall(self):
        # print("Note: this will reboot your machine!")
        time.sleep(5)
        self.conn.sudo(
            "bash {}/install/init_cluster/kubernetes_pre.sh".format(self.root_path))

    def kubernetes_install(self):
        self.conn.sudo(
            "bash {}/install/init_cluster/kubernetes_install.sh".format(self.root_path))
        self.conn.sudo(
            "bash {}/install/init_cluster/kubernetes_post.sh {}".format(self.root_path, self.username))

        # change permissios of kube config. Not working through sh script.
        uid = self.conn.run("id -u").stdout.rstrip()
        gid = self.conn.run("id -g").stdout.rstrip()
        self.conn.sudo(
            "sudo chown {}:{} /users/{}/.kube/config".format(uid, gid, self.username))
        self.conn.sudo(
            "sudo chown {}:{} /users/{}/.kube/".format(uid, gid, self.username))

    def kubernetes_join_workers(self):
        join = self.conn.sudo("sudo kubeadm token create --print-join-command")
        node0_ip = ""
        with open("/etc/hosts", "r") as f:
            for i in f.read().split("\n"):
                if "node0" in i:
                    node0_ip = i.split("\t")[0]
        self.s.sudo(
            "bash {}/install/init_cluster/kubernetes_join.sh {}".format(self.root_path, node0_ip))

        self.s.sudo(join.stdout)
        time.sleep(5)
        self.conn.run("kubectl get nodes")

    def install_nfs(self):

        from kubernetes import client, config

        cmds = []

        cmds.append("helm create {}/nfs-config".format(self.root_path))
        cmds.append("rm -rf {}/nfs-config/templates/*".format(self.root_path))
        cmds.append(
            "cp {}/install/nfs-config/* {}/nfs-config/templates/".format(self.root_path, self.root_path))
        cmds.append(
            "cp {}/install/values.yaml {}/nfs-config/values.yaml".format(self.root_path, self.root_path))
        cmds.append("helm install --namespace={} nfs-config {}/nfs-config/".format(
            self.kube_namespace, self.root_path))

        for cmd in cmds:
            time.sleep(1)
            self.conn.run(cmd)

        label = "role=nfs-server"

        while not check_pod_status(label, self.kube_namespace):
            time.sleep(1)

        config.load_kube_config()
        v1 = client.CoreV1Api()
        pods_list = v1.list_namespaced_pod(
            self.kube_namespace, label_selector=label, watch=False)
        nfs_podname = pods_list.items[0].metadata.name

        cmds = []

        cmds.append('kubectl exec {} -n {} -- /bin/bash -c "rm -rf /exports/*"'.format(
            nfs_podname, self.kube_namespace))
        cmds.append('kubectl exec {} -n {} -- /bin/bash -c "mkdir {}"'.format(
            nfs_podname, self.kube_namespace, self.cerebro_checkpoint_hostpath))
        cmds.append('kubectl exec {} -n {} -- /bin/bash -c "mkdir {}"'.format(
            nfs_podname, self.kube_namespace, self.cerebro_config_hostpath))
        cmds.append('kubectl exec {} -n {} -- /bin/bash -c "mkdir {}"'.format(
            nfs_podname, self.kube_namespace, self.cerebro_data_hostpath))

        with open("{}/install/nfs-config/export.txt".format(self.root_path), "w") as f:
            permissions = "*(rw,insecure,no_root_squash,no_subtree_check)"
            s = "/exports" + "\t" + \
                "*(rw,insecure,fsid=0,no_root_squash,no_subtree_check)" + "\n"
            s += self.cerebro_checkpoint_hostpath + "\t" + permissions + "\n"
            s += self.cerebro_config_hostpath + "\t" + permissions + "\n"
            s += self.cerebro_data_hostpath + "\t" + permissions + "\n"
            f.write(s)
            for i in range(self.w):
                path = self.cerebro_worker_data_hostpath.format(i)
                cmd = 'kubectl exec {} -n {} -- /bin/bash -c "mkdir {}"'.format(
                    nfs_podname, self.kube_namespace, path)
                cmds.append(cmd)
                s = path + "\t" + permissions + "\n"
                f.write(s)

        copy_exports = "kubectl cp -n {} {}/install/nfs-config/export.txt {}:/etc/exports".format(
            self.kube_namespace, self.root_path, nfs_podname)
        reset_exportfs = 'kubectl exec {} -n {} -- /bin/bash -c "exportfs -a"'.format(
            nfs_podname, self.kube_namespace)

        cmds.append(copy_exports)
        cmds.append(reset_exportfs)

        for cmd in cmds:
            self.conn.run(cmd)

        service = v1.read_namespaced_service(
            'nfs-server-service', self.kube_namespace)
        nfs_ip = service.spec.cluster_ip
        with open('{}/install/values.yaml'.format(self.root_path), 'r') as yamlfile:
            values_yaml = yaml.safe_load(yamlfile)
        values_yaml["nfs"]["ip"] = nfs_ip
        with open('{}/install/values.yaml'.format(self.root_path), 'w') as yamlfile:
            yaml.safe_dump(values_yaml, yamlfile)

    def install_metrics_monitor(self):
        import_or_install("kubernetes")
        from kubernetes import client, config

        config.load_kube_config()
        v1 = client.CoreV1Api()

        cmds = [
            "kubectl create namespace prom-metrics",
            "helm repo add prometheus-community https://prometheus-community.github.io/helm-charts",
            "helm repo update",
            "helm install --namespace=prom-metrics prom prometheus-community/kube-prometheus-stack"
        ]

        for cmd in cmds:
            self.conn.run(cmd)

        name = "prom-grafana"
        ns = "prom-metrics"
        body = v1.read_namespaced_service(namespace=ns, name=name)
        body.spec.type = "NodePort"
        v1.patch_namespaced_service(name, ns, body)

        svc = v1.read_namespaced_service(namespace=ns, name=name)
        port = svc.spec.ports[0].node_port

        print(
            "Access Grafana with this link:\nhttp://<Cloudlab Host Name>: {}".format(port))
        print("username: {}\npassword: {}".format("admin", "prom-operator"))

        with open("{}/install/metrics_monitor_credentials.txt".format(self.root_path), "w") as f:
            f.write(
                "Access Grafana with this link:\nhttp://<Cloudlab Host Name>: {}\n".format(port))
            f.write("username: {}\npassword: {}".format(
                "admin", "prom-operator"))

    def init_cerebro_kube(self):
        cmds = [
            "kubectl create -f {}/install/other-configs/rbac_clusterroles.yaml".format(
                self.root_path),
            "kubectl create namespace {}".format(self.kube_namespace),
            "kubectl create -n {} secret generic kube-config --from-file={}".format(
                self.kube_namespace, os.path.expanduser("~/.kube/config")),
            "kubectl config set-context --current --namespace={}".format(
                self.kube_namespace),
            "kubectl create -n {} configmap cerebro-properties --from-file={}/properties/cerebro-properties.json".format(
                self.kube_namespace, self.root_path),
            "kubectl create -n {} configmap hyperparameter-properties --from-file={}/properties/hyperparameter-properties.json".format(
                self.kube_namespace, self.root_path),
        ]

        for cmd in cmds:
            self.conn.run(cmd)

        # install nfs server
        self.install_nfs()
        # install prometheus + grafana
        self.install_metrics_monitor()

    def port_forward_jupyter(self):
        users_port = 9999
        kube_port = 23456

        controller = get_pod_names(self.kube_namespace)[0]
        cmd = "kubectl exec -i {} -- cat JUPYTER_TOKEN".format(controller)
        jupyter_token = self.conn.run(cmd).stdout

        cmd = "kubectl port-forward --address 127.0.0.1 {} {}:8888 &".format(
            controller, kube_port)
        out = self.runbg(cmd)
        user_pf_command = "ssh -N -L {}:localhost:{} {}@<CloudLab host name>".format(
            users_port, kube_port, self.username)
        print("Run this command on your local machine to access Jupyter Notebook : \n{}".format(
            user_pf_command))
        print("http://localhost:{}/?token={}".format(users_port, jupyter_token))

    def install_controller(self):
        from kubernetes import client, config

        cmds = [
            "helm create {}/cerebro-controller".format(self.root_path),
            "rm -rf {}/cerebro-controller/templates/*".format(self.root_path),
            "cp {}/install/controller/config/* {}/cerebro-controller/templates/".format(
                self.root_path, self.root_path),
            "cp {}/install/values.yaml {}/cerebro-controller/values.yaml".format(
                self.root_path, self.root_path),
            "helm install --namespace=cerebro controller {}/cerebro-controller/".format(
                self.root_path)
        ]

        for cmd in cmds:
            time.sleep(1)
            self.conn.run(cmd)

        label = "app=cerebro-controller"

        while not check_pod_status(label, self.kube_namespace):
            time.sleep(1)

        controller = get_pod_names(self.kube_namespace)[0]
        self.runbg(
            "kubectl exec -t {} -- /bin/bash run_jupyter.sh".format(controller))

        self.port_forward_jupyter()
        print("Done")

    def install_worker(self):
        from kubernetes import client, config

        cmds = [
            "helm create {}/cerebro-worker".format(self.root_path),
            "rm -rf {}/cerebro-worker/templates/*".format(self.root_path),
            "cp {}/install/worker/config/* {}/cerebro-worker/templates/".format(
                self.root_path, self.root_path),
            "cp {}/install/values.yaml {}/cerebro-worker/values.yaml".format(
                self.root_path, self.root_path),
        ]
        c = "helm install --namespace={n} worker{id} {path}/cerebro-worker --set workerID={id}"

        for i in range(self.w):
            cmds.append(
                c.format(id=i, path=self.root_path, n=self.kube_namespace))

        for cmd in cmds:
            time.sleep(0.5)
            self.conn.run(cmd)

    def run_dask(self):
        from kubernetes import client, config

        pods = get_pod_names(self.kube_namespace)
        controller = pods[0]
        workers = pods[1:]

        for pod in pods:
            self.conn.run("kubectl exec -t {} -- pip install --upgrade click==8.0.2".format(pod))

        scheduler_cmd = "kubectl exec -it {} -- dask-scheduler --host=0.0.0.0 &".format(
            controller)
        out = self.runbg(scheduler_cmd)

        config.load_kube_config()
        v1 = client.CoreV1Api()
        svc_name = "cerebro-controller-service"
        svc = v1.read_namespaced_service(
            namespace=self.kube_namespace, name=svc_name)
        controller_ip = svc.spec.cluster_ip

        print(controller_ip)
        worker_cmd = "kubectl exec -it {} dask-worker tcp://{}:8786 &"
        for worker in workers:
            self.runbg(worker_cmd.format(worker, controller_ip))

        print("cerebro-controller's IP: ", controller_ip)

    def stop_jupyter(self):
        from kubernetes import client, config

        pods = get_pod_names(self.kube_namespace)
        controller = pods[0]

        out = self.conn.run(
            "kubectl exec -t {} -- ps -ef | grep jupyter-notebook".format(controller))
        notebook_pid = out.stdout.split()[1]
        print(notebook_pid)
        self.conn.run(
            "kubectl exec -t {} -- kill {} || true".format(controller, notebook_pid))
        print("Killed Jupyter Notebook: {}".format(notebook_pid))

    def start_jupyter(self):
        from kubernetes import client, config

        pods = get_pod_names(self.kube_namespace)
        controller = pods[0]

        self.runbg("kubectl exec -it {} -- /bin/bash run_jupyter.sh".format(controller))

    def stop_dask(self):
        from kubernetes import client, config

        pods = get_pod_names(self.kube_namespace)
        controller = pods[0]
        workers = pods[1:]

        out = self.conn.run(
            "kubectl exec -t {} -- ps -ef | grep dask-scheduler".format(controller))
        scheduler_pid = out.stdout.split()[1]
        self.conn.run(
            "kubectl exec -t {} -- kill {} || true".format(controller, scheduler_pid))
        print("Killed Dask Scheduler: {}".format(scheduler_pid))

        for worker in workers:
            out = self.conn.run(
                "kubectl exec -t {} -- ps -ef | grep dask-worker".format(worker))
            worker_pid = out.stdout.split()[1]
            self.conn.run(
                "kubectl exec -t {} -- kill {} || true".format(controller, worker_pid))
            print("Killed Dask in Worker: {}".format(worker_pid))

    def copy_module(self):
        from kubernetes import client, config

        pods = get_pod_names(self.kube_namespace)

        self.conn.run(
            "cd {} && zip cerebro.zip cerebro/*".format(self.root_path))

        for pod in pods:
            self.conn.run(
                "kubectl exec -t {} -- rm -rf /etl-wip/cerebro".format(pod))

        cmds = [
            "kubectl cp {}/cerebro.zip {}:/etl-wip/",
            "kubectl cp {}/requirements.txt {}:/etl-wip/",
            "kubectl cp {}/setup.py {}:/etl-wip/"
        ]
        for pod in pods:
            for cmd in cmds:
                self.conn.run(cmd.format(self.root_path, pod))

        for pod in pods:
            self.conn.run(
                "kubectl exec -t {} -- unzip -o cerebro.zip".format(pod))
            self.conn.run(
                "kubectl exec -t {} -- python3 setup.py install --user".format(pod))

        self.conn.run("rm {}/cerebro.zip".format(self.root_path))

    def download_coco(self):
        pods = get_pod_names(self.kube_namespace)
        self.conn.run("kubectl exec -it {} -- /bin/bash ./install/utilities.sh".format(pods[0]))

    def testing(self):
        self.install_nfs()

    def close(self):
        self.s.close()
        self.conn.close()


def main():
    root_path = "/users/{}/etl-wip"

    kube_params = {
        "kube_namespace": "cerebro",
        "cerebro_checkpoint_hostpath": "/exports/cerebro-checkpoint",
        "cerebro_config_hostpath": "/exports/cerebro-config",
        "cerebro_data_hostpath": "/exports/cerebro-data",
        "cerebro_worker_data_hostpath": "/exports/cerebro-data-{}"
    }

    parser = ArgumentParser()
    parser.add_argument("cmd", help="install dependencies")
    parser.add_argument("-w", "--workers", dest="workers", type=int,
                        help="number of workers")

    args = parser.parse_args()

    installer = CerebroInstaller(root_path, args.workers, kube_params)
    if args.cmd == "init":
        installer.init()
    else:
        installer.init_fabric()
        if args.cmd == "preinstall":
            installer.kubernetes_preinstall()
        elif args.cmd == "install":
            installer.kubernetes_install()
        elif args.cmd == "joinworkers":
            installer.kubernetes_join_workers()
        elif args.cmd == "initcerebrokube":
            installer.init_cerebro_kube()
        elif args.cmd == "installcontroller":
            installer.install_controller()
        elif args.cmd == "installworkers":
            installer.install_worker()
        elif args.cmd == "rundask":
            installer.run_dask()
        elif args.cmd == "startjupyter":
            installer.start_jupyter()
        elif args.cmd == "copymodule":
            installer.copy_module()
        elif args.cmd == "stopdask":
            installer.stop_dask()
        elif args.cmd == "stopjupyter":
            installer.stop_jupyter()
        elif args.cmd == "portforward":
            installer.port_forward_jupyter()
        elif args.cmd == "testing":
            installer.testing()
        elif args.cmd == "downloadcoco":
            installer.download_coco()

    installer.close()


main()

# OTHER COMMANDS
# cat >> ~/.inputrc <<'EOF'
# "\e[A": history-search-backward
# "\e[B": history-search-forward
# EOF
# bind -f  ~/.inputrc

# source <(kubectl completion bash)
# echo "source <(kubectl completion bash)" >> ~/.bashrc 
# alias k=kubectl
# complete -F __start_kubectl k