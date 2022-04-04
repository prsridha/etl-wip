import sys
import pip

def import_or_install(package):
    try:
        __import__(package)
    except ImportError:
        pip.main(['install', package]) 

import_or_install("fabric2")
from fabric2 import SerialGroup, Connection

workers = [
    "128.110.219.138",
    "128.110.219.125",
    "128.110.219.131"
]

user = "vik1497"
host = "128.110.219.134"
pem_path = "/users/vik1497/cloudlab.pem"
connect_kwargs = {"key_filename":pem_path}
conn = Connection(host, user=user, connect_kwargs=connect_kwargs)
s = SerialGroup(*workers, user=user, connect_kwargs=connect_kwargs)


# need to have password sans cloudlab.pem copied to scheduler

# copy cloudlab.pem to workers
def copy_pem():
    result = s.put("/users/vik1497/cloudlab.pem", "/users/vik1497")
    return result

def copy_module():
    print("Zipping cerebro")
    conn.run("zip /users/vik1497/etl-wip/cerebro.zip /users/vik1497/etl-wip/cerebro/*")
    s.run("mkdir -p /users/vik1497/etl-wip/etl-wip")
    s.put("/users/vik1497/etl-wip/cerebro.zip", "/users/vik1497/etl-wip/cerebro.zip")
    s.put("/users/vik1497/etl-wip/requirements.txt", "/users/vik1497/etl-wip/requirements.txt")
    s.put("/users/vik1497/etl-wip/setup.py", "/users/vik1497/etl-wip/setup.py")
    print(s.run("unzip /users/vik1497/etl-wip/cerebro.zip"))
    print(s.run("cd /users/vik1497/etl-wip && python3 setup.py install --user"))

def run(cmd):
    result = s.run(cmd)
    print(result)

def install_dependencies():
    print("Installing dependencies...")

    conn.sudo("sudo apt update")
    conn.sudo("sudo apt install -y python3-pip")
    conn.run("pip install -r /users/vik1497/etl-wip/requirements.txt")

    print("chmod /mydata/")
    conn.sudo("sudo chmod 777 -R /mydata/")

    print("Adding bin dir to path")
    conn.run('echo "export PATH=$PATH:$HOME/.local/bin" >> ~/.bashrc')
    conn.run("source ~/.bashrc")

    print("Installing more dependencies")
    conn.run("pip install click==7.1.1")

    print("Installing dependencies on workers...")
    s.sudo("sudo apt update")
    s.sudo("sudo apt install -y python3-pip")
    run("pip install -r /users/vik1497/etl-wip/requirements.txt")

    print("chmod /mydata/")
    s.sudo("sudo chmod 777 -R /mydata/")

    print("Adding bin dir to path")
    run('echo "export PATH=$PATH:$HOME/.local/bin" >> ~/.bashrc')
    run("source ~/.bashrc")
 
    print("Installing more dependencies")
    run("pip install click==7.1.1")

def delete_coco():
    print("Deleting /mydata/coco")
    s.run("rm -rf /mydata/coco/*")

def testing():
    conn.run("ls -a")

def main():
    args = sys.argv

    # print("GOT: ", args[1] + " " + args[2])
    # print(args[0])
    
    if args[1] == "install":
        install_dependencies()
    elif args[1] == "testing":
        testing() 
    elif args[1] + " " + args[2] == "copy pem":
        out = copy_pem(s)
        print(out)
    elif args[1] + " " + args[2] == "copy module":
        copy_module()
    elif args[1] + " " + args[2] == "delete coco":
        delete_coco()

main()

# OTHER COMMANDS
# cat >> ~/.inputrc <<'EOF'
# "\e[A": history-search-backward
# "\e[B": history-search-forward
# EOF
# bind -f  ~/.inputrc