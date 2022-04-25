import os
import site
import time
import subprocess
from importlib import reload
from argparse import ArgumentParser

# need to have password sans cloudlab.pem copied to scheduler
# sudo ssh-keygen -p -N "" -f ./cloudlab.pem

def import_or_install(package):
    try:
        __import__(package)
    except ImportError:
        import pip
        pip.main(['install', package])
    finally:
        reload(site)

def check_pod_status(label):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    names = []
    pods_list = v1.list_namespaced_pod(
        namespace_, label_selector=label, watch=False)
    for pod in pods_list.items:
        names.append(pod.metadata.name)

    if not names:
        return False

    for i in names:
        pod = v1.read_namespaced_pod_status(i, namespace_, pretty='true')
        status = pod.status.phase
        if status != "Running":
            return False
    return True

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
        self.s = ThreadingGroup(*workers, user=user, connect_kwargs=connect_kwargs)

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
        self.s.run("git clone https://github.com/prsridha/etl-wip.git --branch kubernetes")

    def kubernetes_preinstall(self):
        # print("Note: this will reboot your machine!")
        time.sleep(5)
        self.conn.sudo("bash {}/install/init_cluster/kubernetes_pre.sh".format(self.root_path))

    def kubernetes_install(self):
        self.conn.sudo("bash {}/install/init_cluster/kubernetes_install.sh".format(self.root_path))
        self.conn.sudo("bash {}/install/init_cluster/kubernetes_post.sh {}".format(self.root_path, self.username))
    
    def kubernetes_join_workers(self):
        join = self.conn.sudo("sudo kubeadm token create --print-join-command")
        node0_ip = ""
        with open("/etc/hosts", "r") as f:
            for i in f.read().split("\n"):
                if "node0" in i:
                    node0_ip = i.split("\t")[0]
        self.s.sudo("bash {}/install/init_cluster/kubernetes_join.sh {}".format(self.root_path, node0_ip))

        self.s.sudo(join.stdout)
        time.sleep(5)
        self.conn.run("kubectl get nodes")
    
    def init_cerebro_kube(self):
        cmds = [
            "kubectl create -f {}/install/other-configs/rbac_clusterroles.yaml".format(self.root_path),
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

    def install_nfs(self):
        self.conn.run("helm create {}/nfs-config".format(self.root_path))
        self.conn.run( "rm -rf {}/nfs-config/templates/*".format(self.root_path))
        self.conn.run("cp {}/install/nfs-config/* {}/nfs-config/templates/".format(self.root_path,self.root_path))
        self.conn.run("cp {}/install/values.yaml {}/nfs-config/values.yaml".format(self.root_path,self.root_path))
        self.conn.run("helm install --namespace={} nfs-config {}/nfs-config/".format(self.kube_namespace, self.root_path))

        label = "role=nfs-server"

        """
        while not check_pod_status(label):
            sleep(1)

        config.load_kube_config()
        v1 = client.CoreV1Api()
        pods_list = v1.list_namespaced_pod(
        namespace_, label_selector=label, watch=False)
        nfs_podname = pods_list.items[0].metadata.name

        cmds = []

        cmds.append('kubectl exec {} -n {} -- /bin/bash -c "rm -rf /exports/*"'.format(
            nfs_podname, self.kube_namespace))
        cmds.append('kubectl exec {} -n {} -- /bin/bash -c "mkdir {}"'.format(
            nfs_podname, namespace_, cerebro_checkpoint_hostpath))
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

        """

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
        
        print("Access Grafana with this link:\nhttp://<Cloudlab Host Name>: {}".format(port))
        print("username: {}\npassword: {}".format("admin", "prom-operator"))

        with open("{}/install/metrics_monitor_credentials.txt".format(self.root_path), "w") as f:
            f.write("Access Grafana with this link:\nhttp://<Cloudlab Host Name>: {}\n".format(port))
            f.write("username: {}\npassword: {}".format("admin", "prom-operator"))


    def testing(self):
        # self.conn.run("sudo chown $(id -u):$(id -g) $HOME/.kube/config")
        self.conn.sudo("bash /users/prsridha/etl-wip/install/init_cluster/testing.sh prsridha")

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
        elif args.cmd == "installnfs":
            installer.install_nfs()
        elif args.cmd == "metricsmonitor":
            installer.install_metrics_monitor()
        elif args.cmd == "testing":
            installer.testing()

    installer.close()

main()















































































#####################################################################################################

# # copy cloudlab.pem to workers
# def copy_pem():
#     global s
#     global username

#     result = s.put("/users/{}/cloudlab.pem".format(username),
#                    "/users/{}".format(username))
#     return result



# def init(w):
#     global s
#     global conn
#     global username

#     subprocess.call(["sudo", "apt", "update"])
#     subprocess.call(["sudo", "apt", "install", "-y", "python3-pip"])
#     username = subprocess.run(
#         "whoami", capture_output=True, text=True).stdout.strip("\n")

#     import_or_install("fabric2")
#     import_or_install("dask[complete]")
#     subprocess.call(
#         ["bash", "/users/{}/etl-wip/install/path.sh".format(username)])

#     init_fabric(w)

#     s.run("whoami")
#     s.run("rm -rf /users/{}/etl-wip".format(username))
#     s.run("git clone https://github.com/prsridha/etl-wip.git")

# # copy cloudlab.pem to workers
# def copy_pem():
#     global s
#     global username

#     result = s.put("/users/{}/cloudlab.pem".format(username),
#                    "/users/{}".format(username))
#     return result


# def copy_module():
#     global s
#     global conn
#     global username

#     print("Zipping cerebro")
#     conn.run(
#         "zip /users/{}/etl-wip/cerebro.zip /users/{}/etl-wip/cerebro/*".format(username, username))
#     s.run("mkdir -p /users/{}/etl-wip/etl-wip".format(username))
#     s.put("/users/{}/etl-wip/cerebro.zip".format(username),
#           "/users/{}/etl-wip/cerebro.zip".format(username))
#     s.put("/users/{}/etl-wip/requirements.txt".format(username),
#           "/users/{}/etl-wip/requirements.txt".format(username))
#     s.put("/users/{}/etl-wip/setup.py".format(username),
#           "/users/{}/etl-wip/setup.py".format(username))
#     print(s.run("unzip /users/{}/etl-wip/cerebro.zip".format(username)))
#     print(s.run("cd /users/{}/etl-wip && python3 setup.py install --user".format(username)))


# def run(cmd):
#     global s

#     result = s.run(cmd)
#     print(result)


# def start_dask():
#     global s
#     global conn
#     global username

#     print("Starting Dask Scheduler")
#     conn.run("dask-scheduler --host=0.0.0.0")
#     print("Starting Dask workers")
#     s.run("dask-worker tcp://128.110.219.134:8786")


# def install_dependencies():
#     global s
#     global conn
#     global username

#     print("Installing dependencies...")

#     conn.sudo("sudo apt update")
#     conn.sudo("sudo apt install -y python3-pip")
#     conn.run("pip install -r /users/{}/etl-wip/requirements.txt".format(username))

#     print("chmod /mydata/")
#     conn.sudo("sudo chmod 777 -R /mydata/")

#     conn.sudo("sudo apt install dtach")

#     print("Adding bin dir to path")
#     conn.run("bash /users/{}/etl-wip/install/path.sh".format(username))

#     print("Installing more dependencies")
#     conn.run("pip install click==7.1.1")

#     print("Installing dependencies on workers...")
#     s.sudo("sudo apt update")
#     s.sudo("sudo apt install -y python3-pip")
#     run("pip install -r /users/{}/etl-wip/requirements.txt".format(username))

#     print("chmod /mydata/")
#     s.sudo("sudo chmod 777 -R /mydata/")

#     s.sudo("sudo apt install dtach")

#     print("Adding bin dir to path")
#     s.put("/users/{}/etl-wip/install/path.sh".format(username),
#           "/users/{}/".format(username))
#     s.run("bash /users/{}/path.sh".format(username))

#     print("Installing more dependencies")
#     run("pip install click==7.1.1")


# def delete_coco():
#     global s
#     global conn
#     global username

#     print("Deleting /mydata/coco")
#     s.run("rm -rf /mydata/coco/*")


# def runbg(pre, cmd, sockname="dtach"):
#     return pre.run('dtach -n `mktemp -u /tmp/%s.XXXX` %s' % (sockname, cmd))


# def testing():
#     global s
#     global conn
#     global username

#     # s.put("/users/prsridha/etl-wip/path.sh", "/users/prsridha")
#     conn.run("bash /users/prsridha/etl-wip/path.sh")


# def setup_dask():
#     global s
#     global conn
#     global username

#     from distributed.utils import get_ip
#     cmd1 = 'nohup bash -c "/users/{}/.local/bin/dask-scheduler --host=0.0.0.0"'.format(
#         username)
#     cmd2 = 'nohup bash -c "/users/{}/.local/bin/dask-worker tcp://{}:8786"'.format(
#         username, get_ip())
#     runbg(conn, cmd1)
#     runbg(s, cmd2)
#     print("Done")


# def kill_dask():
#     global s
#     global conn
#     global username

#     user = username
#     pem_path = "/users/{}/cloudlab.pem".format(username)
#     connect_kwargs = {"key_filename": pem_path}
#     from fabric2 import SerialGroup, Connection

#     out = conn.run("ps -ef | grep dask-scheduler")
#     scheduler_pid = out.stdout.split()[1]
#     conn.run("kill {} || true".format(scheduler_pid))
#     print("Killed Scheduler: {}".format(scheduler_pid))

#     worker_pids = []
#     out = s.run("ps -ef | grep dask-worker")
#     # pid = out.stdout.split()[1]
#     for idx, i in enumerate(out.values()):
#         pid = i.stdout.split()[1]
#         worker_pids.append(pid)
#         temp_conn = Connection("node"+str(idx), user=user,
#                                connect_kwargs=connect_kwargs)
#         temp_conn.run("kill {} || true".format(pid))
#         print("Killed Worker: {}".format(pid))
#         temp_conn.close()
#     print(worker_pids)


# def main():
#     parser = ArgumentParser()
#     parser.add_argument("cmd", help="install dependencies")
#     parser.add_argument("-w", "--workers", dest="workers", type=int,
#                         help="number of workers")

#     args = parser.parse_args()

#     if args.cmd == "install":
#         init(args.workers)
#         install_dependencies()
#     else:
#         init_fabric(args.workers)
#         if args.cmd == "testing":
#             testing()
#         elif args.cmd == "copypem":
#             out = copy_pem()
#             print(out)
#         elif args.cmd == "copymodule":
#             copy_module()
#         elif args.cmd == "deletecoco":
#             delete_coco()
#         elif args.cmd == "setupdask":
#             setup_dask()
#         elif args.cmd == "killdask":
#             kill_dask()

#     conn.close()
#     s.close()


# main()

# OTHER COMMANDS
# cat >> ~/.inputrc <<'EOF'
# "\e[A": history-search-backward
# "\e[B": history-search-forward
# EOF
# bind -f  ~/.inputrc
