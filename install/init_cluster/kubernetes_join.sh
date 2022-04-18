#!/bin/bash

## become root
apt-get update && apt-get upgrade -y

## install docker
apt-get install -y docker.io

## ONLY FOR OPENSTACK
mkdir /mnt/docker 
service docker stop
sleep 5
echo "-g /mnt/docker" > /etc/default/docker
mv /var/lib/docker /mnt/
ln -s /mnt/docker /var/lib/docker
service docker start

sudo apt install nfs-kernel-server

## add repo, GPG for kube
echo "deb http://apt.kubernetes.io/ kubernetes-xenial main" > /etc/apt/sources.list.d/kubernetes.list
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
apt-get update

## install kubeadm, kubelet, kubectl
apt-get install -y kubeadm=1.18.1-00 kubelet=1.18.1-00 kubectl=1.18.1-00

# turn off swap memory
swapoff -a
sed -i '/ swap / s/^/#/' /etc/fstab

## fix docker issue
touch /etc/docker/daemon.json
echo "{
  \"exec-opts\": [\"native.cgroupdriver=systemd\"]
}
" >> /etc/docker/daemon.json
systemctl daemon-reload
systemctl restart docker
systemctl restart kubelet

# Paste the IPV4 addr from master
echo -e "$1\tk8smaster" >> /etc/hosts