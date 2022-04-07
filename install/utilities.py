import subprocess
from argparse import ArgumentParser

# need to have password sans cloudlab.pem copied to scheduler
# sudo ssh-keygen -p -N "" -f ./cloudlab.pem

def import_or_install(package):
    try:
        __import__(package)
    except ImportError:
        import pip
        pip.main(['install', package])


def init(w):
    global conn
    global s

    subprocess.call(["sudo", "apt", "update"])
    subprocess.call(["sudo", "apt", "install", "-y", "python3-pip"])
    
    import_or_install("fabric2")
    import_or_install("dask[complete]")
    subprocess.call(["bash", "/users/vik1497/etl-wip/install/path.sh"])
    from fabric2 import SerialGroup, Connection

    workers = ["node"+str(i) for i in range(w)]
    host = "node0"

    #initialize fabric
    user = "vik1497"
    pem_path = "/users/vik1497/cloudlab.pem"
    connect_kwargs = {"key_filename": pem_path}
    conn = Connection(host, user=user, connect_kwargs=connect_kwargs)
    s = SerialGroup(*workers, user=user, connect_kwargs=connect_kwargs)

    s.run("git clone https://github.com/prsridha/etl-wip.git")
# copy cloudlab.pem to workers


def copy_pem():
    result = s.put("/users/vik1497/cloudlab.pem", "/users/vik1497")
    return result


def copy_module():
    print("Zipping cerebro")
    conn.run("zip /users/vik1497/etl-wip/cerebro.zip /users/vik1497/etl-wip/cerebro/*")
    s.run("mkdir -p /users/vik1497/etl-wip/etl-wip")
    s.put("/users/vik1497/etl-wip/cerebro.zip",
          "/users/vik1497/etl-wip/cerebro.zip")
    s.put("/users/vik1497/etl-wip/requirements.txt",
          "/users/vik1497/etl-wip/requirements.txt")
    s.put("/users/vik1497/etl-wip/setup.py", "/users/vik1497/etl-wip/setup.py")
    print(s.run("unzip /users/vik1497/etl-wip/cerebro.zip"))
    print(s.run("cd /users/vik1497/etl-wip && python3 setup.py install --user"))


def run(cmd):
    result = s.run(cmd)
    print(result)


def start_dask():
    print("Starting Dask Scheduler")
    conn.run("dask-scheduler --host=0.0.0.0")
    print("Starting Dask workers")
    s.run("dask-worker tcp://128.110.219.134:8786")


def install_dependencies():
    print("Installing dependencies...")

    conn.sudo("sudo apt update")
    conn.sudo("sudo apt install -y python3-pip")
    conn.run("pip install -r /users/vik1497/etl-wip/requirements.txt")

    print("chmod /mydata/")
    conn.sudo("sudo chmod 777 -R /mydata/")

    conn.sudo("sudo apt install dtach")

    print("Adding bin dir to path")
    # conn.run("bash /users/vik1497/etl-wip/install/path.sh")

    print("Installing more dependencies")
    conn.run("pip install click==7.1.1")

    print("Installing dependencies on workers...")
    s.sudo("sudo apt update")
    s.sudo("sudo apt install -y python3-pip")
    run("pip install -r /users/vik1497/etl-wip/requirements.txt")

    print("chmod /mydata/")
    s.sudo("sudo chmod 777 -R /mydata/")

    s.sudo("sudo apt install dtach")

    print("Adding bin dir to path")
    s.put("/users/vik1497/etl-wip/install/path.sh", "/users/vik1497/")
    s.run("bash /users/vik1497/path.sh")

    print("Installing more dependencies")
    run("pip install click==7.1.1")


def delete_coco():
    print("Deleting /mydata/coco")
    s.run("rm -rf /mydata/coco/*")


def runbg(pre, cmd, sockname="dtach"):
    return pre.run('dtach -n `mktemp -u /tmp/%s.XXXX` %s' % (sockname, cmd))


def testing():
    # s.put("/users/vik1497/etl-wip/path.sh", "/users/vik1497")
    conn.run("bash /users/vik1497/etl-wip/path.sh")


def setup_dask():
    from distributed.utils import get_ip
    cmd1 = 'nohup bash -c "/users/vik1497/.local/bin/dask-scheduler --host=0.0.0.0"'
    cmd2 = 'nohup bash -c "/users/vik1497/.local/bin/dask-worker tcp://{}:8786"'
    runbg(conn, cmd1)
    runbg(s, cmd2.format(get_ip()))
    print("Done")


def kill_dask():
    user = "vik1497"
    pem_path = "/users/vik1497/cloudlab.pem"
    connect_kwargs = {"key_filename": pem_path}
    from fabric2 import SerialGroup, Connection

    out = conn.run("ps -ef | grep dask-scheduler")
    scheduler_pid = out.stdout.split()[1]
    conn.run("kill {} || true".format(scheduler_pid))
    print("Killed Scheduler: {}".format(scheduler_pid))

    worker_pids = []
    out = s.run("ps -ef | grep dask-worker")
    # pid = out.stdout.split()[1]
    for idx, i in enumerate(out.values()):
        pid = i.stdout.split()[1]
        worker_pids.append(pid)
        temp_conn = Connection("node"+str(idx), user=user,
                               connect_kwargs=connect_kwargs)
        temp_conn.run("kill {} || true".format(pid))
        print("Killed Worker: {}".format(pid))
        temp_conn.close()
    print(worker_pids)


def main():
    parser = ArgumentParser()
    parser.add_argument("cmd", help="install dependencies")
    parser.add_argument("-w", "--workers", dest="workers", type=int,
                        help="number of workers")

    args = parser.parse_args()
    init(args.workers)

    if args.cmd == "install":
        install_dependencies()
    elif args.cmd == "testing":
        testing()
    elif args.cmd == "copypem":
        out = copy_pem(s)
        print(out)
    elif args.cmd == "copymodule":
        copy_module()
    elif args.cmd == "deletecoco":
        delete_coco()
    elif args.cmd == "setupdask":
        setup_dask()
    elif args.cmd == "killdask":
        kill_dask()

    conn.close()
    s.close()


main()

# OTHER COMMANDS
# cat >> ~/.inputrc <<'EOF'
# "\e[A": history-search-backward
# "\e[B": history-search-forward
# EOF
# bind -f  ~/.inputrc
