import site
import time
import subprocess
from importlib import reload
from argparse import ArgumentParser
from kubernetes import client, config

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

class CerebroInstaller:
    def __init__(self, root_path, workers):
        self.w = workers
        self.root_path = root_path
        
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
            ["bash", "{}/path.sh".format(self.root_path)])

        self.init_fabric()

        self.s.run("whoami")
        self.s.run("rm -rf /users/{}/etl-wip".format(self.username))
        self.s.run("git clone https://github.com/prsridha/etl-wip.git --branch kubernetes")

    def kubernetes_preinstall(self):
        # print("Note: this will reboot your machine!")
        time.sleep(5)
        self.conn.sudo("bash {}/kubernetes_pre.sh".format(self.root_path))

    def kubernetes_install(self):
        self.conn.sudo("bash {}/kubernetes_install.sh".format(self.root_path))
        self.conn.sudo("bash {}/kubernetes_post.sh {}".format(self.root_path, self.username))

    def kubernetes_join_workers(self):
        join = self.conn.sudo("sudo kubeadm token create --print-join-command")
        node0_ip = ""
        with open("/etc/hosts", "r") as f:
            for i in f.read().split("\n"):
                if "node0" in i:
                    node0_ip = i.split("\t")[0]
        self.s.sudo("bash {}/kubernetes_join.sh {}".format(self.root_path, node0_ip))

        self.s.sudo(join.stdout)
        time.sleep(5)
        self.conn.run("kubectl get nodes")
    
    def install_nfs(self):
        pass
    
    def install_metrics_monitor(self):
        config.load_kube_config()
        v1 = client.CoreV1Api()

        self.conn.run("kubectl create namespace prom-metrics")
        self.conn.run("helm repo add prometheus-community https://prometheus-community.github.io/helm-charts")
        self.conn.run("helm repo update")
        self.conn.run("helm install --namespace=prom-metrics prom prometheus-community/kube-prometheus-stack")

        name = "prom-grafana"
        ns = "prom-metrics"
        body = v1.read_namespaced_service(namespace=ns, name=name)
        body.spec.type = "NodePort"
        v1.patch_namespaced_service(name, ns, body)

        svc = v1.read_namespaced_service(namespace=ns, name=name)
        port = svc.spec.ports[0].node_port
        
        print("Access Grafana with this link:\n http://<Cloudlab Host Name>: {}".format(port))
        print("username{}\npassword:{}".format("admin", "prom-operator"))

    def testing(self):
        # self.conn.run("sudo chown $(id -u):$(id -g) $HOME/.kube/config")
        self.conn.sudo("bash /users/prsridha/etl-wip/install/init_cluster/testing.sh prsridha")

    def close(self):
        self.s.close()
        self.conn.close()

def main():
    root_path = "/users/{}/etl-wip/install/init_cluster"

    parser = ArgumentParser()
    parser.add_argument("cmd", help="install dependencies")
    parser.add_argument("-w", "--workers", dest="workers", type=int,
                        help="number of workers")

    args = parser.parse_args()

    installer = CerebroInstaller(root_path, args.workers)
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
