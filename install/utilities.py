import os
import site
import subprocess
from importlib import reload
from argparse import ArgumentParser
from pathlib import Path
import shutil
from fabric2 import Connection
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


def init_fabric(w):
    global s
    global conn
    global username

    from fabric2 import ThreadingGroup, Connection

    workers = ["node"+str(i) for i in range(1, w+1)]
    host = "node0"
    username = subprocess.run(
        "whoami", capture_output=True, text=True).stdout.strip("\n")

    #initialize fabric
    user = username
    pem_path = "/users/{}/cloudlab.pem".format(username)
    connect_kwargs = {"key_filename": pem_path}
    conn = Connection(host, user=user, connect_kwargs=connect_kwargs)
    s = ThreadingGroup(*workers, user=user, connect_kwargs=connect_kwargs)


def init(w):
    global s
    global conn
    global username

    subprocess.call(["sudo", "apt", "update"])
    subprocess.call(["sudo", "apt", "install", "-y", "python3-pip"])
    username = subprocess.run(
        "whoami", capture_output=True, text=True).stdout.strip("\n")

    import_or_install("fabric2")
    import_or_install("dask[complete]")
    subprocess.call(
        ["bash", "/users/{}/etl-wip/install/path.sh".format(username)])

    init_fabric(w)

    s.run("whoami")
    s.run("rm -rf /users/{}/etl-wip".format(username))
    s.run("git clone https://github.com/prsridha/etl-wip.git")
# copy cloudlab.pem to workers


def copy_pem():
    global s
    global username

    result = s.put("/users/{}/cloudlab.pem".format(username),
                   "/users/{}".format(username))
    return result


def copy_module():
    global s
    global conn
    global username

    print("Zipping cerebro")
    conn.run(
        "zip /users/{}/etl-wip/cerebro.zip /users/{}/etl-wip/cerebro/*".format(username, username))
    s.run("mkdir -p /users/{}/etl-wip/etl-wip".format(username))
    s.put("/users/{}/etl-wip/cerebro.zip".format(username),
          "/users/{}/etl-wip/cerebro.zip".format(username))
    s.put("/users/{}/etl-wip/requirements.txt".format(username),
          "/users/{}/etl-wip/requirements.txt".format(username))
    s.put("/users/{}/etl-wip/setup.py".format(username),
          "/users/{}/etl-wip/setup.py".format(username))
    print(s.run("unzip -o /users/{}/etl-wip/cerebro.zip".format(username)))
    print(s.run("cd /users/{}/etl-wip && python3 setup.py install --user".format(username)))


def run(cmd):
    global s

    result = s.run(cmd)
    print(result)


def start_dask():
    global s
    global conn
    global username

    print("Starting Dask Scheduler")
    conn.run("dask-scheduler --host=0.0.0.0")
    print("Starting Dask workers")
    s.run("dask-worker tcp://128.110.219.134:8786")


def install_dependencies():
    global s
    global conn
    global username

    print("Installing dependencies...")

    conn.sudo("sudo apt update")
    conn.sudo("sudo apt install -y python3-pip")
    conn.run("pip install -r /users/{}/etl-wip/requirements.txt".format(username))

    print("chmod /mydata/")
    conn.sudo("sudo chmod 777 -R /mydata/")

    conn.sudo("sudo apt install dtach")
    conn.sudo("sudo apt install gawk")
    conn.sudo("sudo apt-get install sysstat -y")

    print("Adding bin dir to path")
    conn.run("bash /users/{}/etl-wip/install/path.sh".format(username))

    print("Installing more dependencies")
    conn.run("pip install click==7.1.1")

    print("Installing dependencies on workers...")
    s.sudo("sudo apt update")
    s.sudo("sudo apt install -y python3-pip")
    run("pip install -r /users/{}/etl-wip/requirements.txt".format(username))

    print("chmod /mydata/")
    s.sudo("sudo chmod 777 -R /mydata/")

    s.sudo("sudo apt install dtach")

    s.sudo("sudo apt install gawk")
    s.sudo("sudo apt-get install sysstat -y")

    print("Adding bin dir to path")
    s.put("/users/{}/etl-wip/install/path.sh".format(username),
          "/users/{}/".format(username))
    s.run("bash /users/{}/path.sh".format(username))

    print("Installing more dependencies")
    run("pip install click==7.1.1")


def delete_coco():
    global s
    global conn
    global username
    
    if os.path.isdir("/mydata/coco"):
        print("Deleting /mydata/coco")
        s.run("rm -rf /mydata/coco/")
    else:
        print("/mydata/coco not found")


def runbg(pre, cmd, sockname="dtach"):
    return pre.run('dtach -n `mktemp -u /tmp/%s.XXXX` %s' % (sockname, cmd))


def testing():
    global s
    global conn
    global username

    # s.put("/users/prsridha/etl-wip/path.sh", "/users/prsridha")
    conn.run("bash /users/prsridha/etl-wip/path.sh")


def setup_dask():
    global s
    global conn
    global username

    from distributed.utils import get_ip
    cmd1 = 'nohup bash -c "/users/{}/.local/bin/dask-scheduler --host=0.0.0.0"'.format(
        username)
    cmd2 = 'nohup bash -c "/users/{}/.local/bin/dask-worker tcp://{}:8786"'.format(
        username, get_ip())
    runbg(conn, cmd1)
    runbg(s, cmd2)
    print("Done")


def kill_dask():
    global s
    global conn
    global username

    user = username
    pem_path = "/users/{}/cloudlab.pem".format(username)
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


def run_benchmark_scripts(args):
    global s
    global conn
    global username

    workers = ["node"+str(i) for i in range(1, args.workers+1)]
    pem_path = "/users/{}/cloudlab.pem".format(username)
    connect_kwargs = {"key_filename": pem_path}
    user = username
    for i in range(len(workers)):
        cmd1 = 'nohup bash -c "sh /users/{}/logger_w{}.sh /users/{}/log/"'.format(username, str(i), username)
        print(cmd1)
        temp_conn = Connection(workers[i], user=user,
                               connect_kwargs=connect_kwargs)
        runbg(temp_conn, cmd1)
        temp_conn.close()
    
    print("Done running benchmark scripts")



def kill_benchmark_scripts(args):
    global s
    global conn
    global username

    user = username
    pem_path = "/users/{}/cloudlab.pem".format(username)
    connect_kwargs = {"key_filename": pem_path}
    from fabric2 import Connection

    worker_pids = []
    out = s.run("ps aux | grep logger")
    # pid = out.stdout.split()[1]
    for idx, i in enumerate(out.values()):
        pid = i.stdout.split()[1]
        print(pid, idx)
        worker_pids.append(pid)
        temp_conn = Connection("node"+str(idx), user=user,
                               connect_kwargs=connect_kwargs)
        temp_conn.run("kill {} || true".format(pid))
        print("Killed script: {}".format(pid))
        temp_conn.close()
    print(worker_pids)

def delete_benchmark_scripts():
    pass

def download_logs(args):
    global s
    global conn
    global username
    
    common_logs_path = "/users/{}/etl-wip/benchmark_scripts/logs/".format(username)
    dirpath = Path(common_logs_path)
    if dirpath.exists() and dirpath.is_dir():
        shutil.rmtree(dirpath)
    os.mkdir(dirpath)

    workers = ["node"+str(i) for i in range(1, args.workers+1)]
    pem_path = "/users/{}/cloudlab.pem".format(username)
    connect_kwargs = {"key_filename": pem_path}
    user = username
    for i in range(len(workers)):
        cpu_log_file_name = "/users/{}/log/cpu_util_{}.log".format(username, str(i))
        disk_log_file_name = "/users/{}/log/disk_util_{}.log".format(username, str(i))
        nw_log_file_name = "/users/{}/log/nw_util_{}.log".format(username, str(i))
        temp_conn = Connection(workers[i], user=user,
                               connect_kwargs=connect_kwargs)
        temp_conn.get(cpu_log_file_name, common_logs_path)
        temp_conn.get(disk_log_file_name, common_logs_path)
        temp_conn.get(nw_log_file_name, common_logs_path)
        temp_conn.close()
    print("downloaded log files from workers")

def create_benchmark_scripts(args):
    global username
    base_path="/users/{}/etl-wip/benchmark_scripts/".format(username)
    dirpath = Path(base_path)
    if dirpath.exists() and dirpath.is_dir():
        shutil.rmtree(dirpath)
    os.mkdir(dirpath)
    flines = [
        "#!/usr/bin/env bash\n",
        'if [ "$1" != "" ]; then\n',
        '\tLOG_DIR="$1"\n',
        '\tmkdir -p $LOG_DIR\n',
        'else\n',
        '\tLOG_DIR="."\n',
        'fi\n',
        'LOG_DIR=$1\n'
    ]
    comp_loop = [
        'while true;\n',
        'do\n',
        '\tdatestr=`date "+%Y-%m-%d %H:%M:%S"`\n',
        '\tcpu="$[100-$(vmstat 1 2|tail -1|awk \'{print $15}\')]%"\n',
        '\tmem=$(free | grep Mem | awk \'{print $3/$2 * 100.0 "%"}\')\n',
        '\techo -e "${datestr}\\n${cpu},${mem}" >> $CPU_LOG_FILENAME;\n',
        '\tdisk_log=$(iostat -dm 1 1 | sed \'1,2d\')\n',
        '\techo -e "${datestr}\\n${disk_log}" >> $DISK_LOG_FILENAME;\n',
        '\tmsg_control=$(sudo sar -n DEV 1 1 | grep eno1 | tail -n 1 | gawk \'{print "eno1: "$2", rxpck/s: "$3", txpck/s: "$4", rxkB/s: "$5", txkB/s: "$6", rxcmp/s: "$7", txcmp/s: "$8", rxmcst/s: "$9", %ifutil: "$10}\')\n',
        '\techo -e "${datestr}\\n${msg_control}" >> $NW_LOG_FILENAME;\n',
        '\tsleep 1;\n',
        'done\n'
    ]
    for i in range(args.workers):
        log_script = base_path + "logger_w" + str(i) + ".sh"
        cpu_log_file_name = "CPU_LOG_FILENAME=$LOG_DIR/cpu_util_" + str(i) + ".log\n"
        disk_log_file_name = "DISK_LOG_FILENAME=$LOG_DIR/disk_util_" + str(i) + ".log\n"
        network_log_file_name = "NW_LOG_FILENAME=$LOG_DIR/nw_util_" + str(i) + ".log\n"
        with open(log_script, "a") as ls:
            ls.writelines(flines)
            ls.write(cpu_log_file_name)
            ls.write(disk_log_file_name)
            ls.write(network_log_file_name)
            ls.writelines(comp_loop)

    workers = ["node"+str(i) for i in range(1, args.workers+1)]
    pem_path = "/users/{}/cloudlab.pem".format(username)
    connect_kwargs = {"key_filename": pem_path}
    user = username
    for i in range(len(workers)):
        log_script = base_path + "logger_w" + str(i) + ".sh"
        temp_conn = Connection(workers[i], user=user,
                               connect_kwargs=connect_kwargs)
        temp_conn.put(log_script, "/users/{}".format(user))
        temp_conn.close()
    print("put log files in workers")

def main():
    parser = ArgumentParser()
    parser.add_argument("cmd", help="install dependencies")
    parser.add_argument("-w", "--workers", dest="workers", type=int,
                        help="number of workers")

    args = parser.parse_args()

    if args.cmd == "install":
        init(args.workers)
        install_dependencies()
    else:
        init_fabric(args.workers)
        if args.cmd == "testing":
            testing()
        elif args.cmd == "copypem":
            out = copy_pem()
            print(out)
        elif args.cmd == "copymodule":
            copy_module()
        elif args.cmd == "deletecoco":
            delete_coco()
        elif args.cmd == "setupdask":
            setup_dask()
        elif args.cmd == "killdask":
            kill_dask()
        elif args.cmd == "createscripts":
            create_benchmark_scripts(args)
        elif args.cmd == "runbs":
            run_benchmark_scripts(args)
        elif args.cmd == "killbs":
            kill_benchmark_scripts(args)
        elif args.cmd == "downloadlogs":
            download_logs(args)

    conn.close()
    s.close()


main()

# OTHER COMMANDS
# cat >> ~/.inputrc <<'EOF'
# "\e[A": history-search-backward
# "\e[B": history-search-forward
# EOF
# bind -f  ~/.inputrc
