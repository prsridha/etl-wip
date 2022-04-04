import sys
import pip
from fabric2 import SerialGroup
from invoke import run as local

workers = [
    "128.110.218.38",
    "128.110.218.32",
    "128.110.218.17"
]

# need to have password sans cloudlab.pem copied to scheduler

# copy cloudlab.pem to workers
def copy_pem():
    result = s.put("/users/vik1497/cloudlab.pem", "/users/vik1497")
    return result

def copy_module():
    print("Zipping cerebro")
    local("zip /users/vik1497/etl-wip/cerebro.zip /users/vik1497/etl-wip/cerebro/*")
    s.run("mkdir -p /users/vik1497/etl-wip/etl-wip")
    s.put("/users/vik1497/etl-wip/cerebro.zip", "/users/vik1497/etl-wip/cerebro.zip")
    s.put("/users/vik1497/etl-wip/requirements.txt", "/users/vik1497/etl-wip/requirements.txt")
    s.put("/users/vik1497/etl-wip/setup.py", "/users/vik1497/etl-wip/setup.py")
    print(s.run("unzip /users/vik1497/etl-wip/cerebro.zip"))
    print(s.run("cd /users/vik1497/etl-wip && python3 setup.py install --user"))

def run(cmd):
    result = s.run(cmd)
    print(rcesult)

def install_dependencies():
    print("Installing dependencies...")
    run("sudo apt update")
    run("sudo apt install -y python3-pip")
    run("pip install -r requirements.txt")

    print("chmod /mydata/")
    run("sudo chmod 777 -R /mydata/")

    print "Adding bin dir to path"
    run('echo "export PATH=$PATH:$HOME/.local/bin" >> ~/.bashrc')
    run("source ~/.bashrc")

    print("Installing more dependencies")
    run("pip install click==6.6")

def main():
    args = sys.argv
    
    if args[0] + " " + args[1] == "copy pem":
        out = copy_pem(s)
        print(out)
    elif args[0] + " " + args[1] == "copy module":
        copy_module()
    elif args[0] == "install":
        install_dependencies()


# OTHER COMMANDS
# cat >> ~/.inputrc <<'EOF'
# "\e[A": history-search-backward
# "\e[B": history-search-forward
# EOF
# bind -f  ~/.inputrc