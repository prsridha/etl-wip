#!/bin/bash

## post installation steps - 
# run as non-root ->
mkdir -p /users/$1/.kube
#TODO: asks for user input- fix it
sudo cp -rf -y /etc/kubernetes/admin.conf /users/$1/.kube/config
# sudo chown $(id -u $1):$(id -g $1) /users/$1/.kube/config
# sudo chown $(id -u $1):$(id -g $1) /users/$1/.kube/
sudo cp /root/calico.yaml .
kubectl apply -f calico.yaml
kubectl taint nodes $(hostname) node-role.kubernetes.io/master:NoSchedule-


## increase space of node
# sudo /usr/local/etc/emulab/mkextrafs.pl /mnt
sudo apt install nfs-kernel-server

## install helm
curl https://baltocdn.com/helm/signing.asc | sudo apt-key add -
echo "deb https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
sudo apt-get update
sudo apt-get install helm
sudo apt-get -y install jq
sudo apt -y install python3-pip
pip install kubernetes
sudo apt-get install apt-transport-https --yes


## ONLY FOR OPENSTACK
# dpkg -l 'linux-*' | sed '/^ii/!d;/'"$(uname -r | sed "s/\(.*\)-\([^0-9]\+\)/\1/")"'/d;s/^[^ ]* [^ ]* \([^ ]*\).*/\1/;/[0-9]/!d' | xargs sudo apt-get -y purge

## extra stuff (optional)
# setup command autocompletion
# sudo apt-get install bash-completion -y
# source <(kubectl completion bash)
# echo "source <(kubectl completion bash)" >> ~/.bashrc
# alias k=kubectl
# complete -F __start_kubectl k

# cat >> ~/.inputrc <<'EOF'
# "\e[A": history-search-backward
# "\e[B": history-search-forward
# EOF
# bind -f  ~/.inputrc#!/bin/bash

## post installation steps - 
# run as non-root ->
mkdir -p /users/prsridha/.kube
sudo cp -i /etc/kubernetes/admin.conf /users/prsridha/.kube/config
sudo chown $(id -u):$(id -g) /users/prsridha/.kube/config
sudo cp /root/calico.yaml .
kubectl apply -f calico.yaml
kubectl taint nodes $(hostname) node-role.kubernetes.io/master:NoSchedule-

## increase space of node
# sudo /usr/local/etc/emulab/mkextrafs.pl /mnt
sudo apt install nfs-kernel-server
sudo chmod -R 777 /mnt
sudo chmod 666 /var/run/docker.sock

## install helm
curl https://baltocdn.com/helm/signing.asc | sudo apt-key add -
echo "deb https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
sudo apt-get update
sudo apt-get install helm
sudo apt-get -y install jq
sudo apt -y install python3-pip
pip install kubernetes
sudo apt-get install apt-transport-https --yes
sudo apt-get install dtach

## ONLY FOR OPENSTACK
# dpkg -l 'linux-*' | sed '/^ii/!d;/'"$(uname -r | sed "s/\(.*\)-\([^0-9]\+\)/\1/")"'/d;s/^[^ ]* [^ ]* \([^ ]*\).*/\1/;/[0-9]/!d' | xargs sudo apt-get -y purge

## extra stuff (optional)
# setup command autocompletion
# sudo apt-get install bash-completion -y
# source <(kubectl completion bash)
# echo "source <(kubectl completion bash)" >> ~/.bashrc
# alias k=kubectl
# complete -F __start_kubectl k

# cat >> ~/.inputrc <<'EOF'
# "\e[A": history-search-backward
# "\e[B": history-search-forward
# EOF
# bind -f  ~/.inputrc