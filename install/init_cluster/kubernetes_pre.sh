#!/bin/bash

## become root
apt-get update && apt-get upgrade -y

## install docker
apt-get install -y docker.io

## ONLY FOR OPENSTACK
# mkdir /mnt/docker
# echo "-g /mnt/docker" > /etc/default/docker
# service docker stop
# mv /var/lib/docker /mnt/
# ln -s /mnt/docker /var/lib/docker
# service docker start

## add repo, GPG for kube
echo "deb http://apt.kubernetes.io/ kubernetes-xenial main" > /etc/apt/sources.list.d/kubernetes.list
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
apt-get update

## install kubeadm, kubelet, kubectl
apt-get install -y kubeadm=1.18.1-00 kubelet=1.18.1-00 kubectl=1.18.1-00

# uncomment the line with "CALICO_IPV4POOL_CIDR" and the line below it
wget https://docs.projectcalico.org/manifests/calico.yaml
sed -i '/# - name: CALICO_IPV4POOL_CIDR/c\            - name: CALICO_IPV4POOL_CIDR' ./calico.yaml
sed -i '/#   value: "192.168.0.0\/16"/c\              value: "192.168.0.0\/16"' ./calico.yaml

# copy the following lines to the yaml file
touch kubeadm-config.yaml
echo "apiVersion: kubeadm.k8s.io/v1beta2
kind: ClusterConfiguration
kubernetesVersion: 1.18.1               #<-- Use the word stable for newest version
controlPlaneEndpoint: "k8smaster:6443"  #<-- Use the node alias not the IP
networking:
  podSubnet: 192.168.0.0/16             #<-- Match the IP range from the Calico config file
" > kubeadm-config.yaml

# turn off swap memory
swapoff -a
sed -i '/ swap / s/^/#/' /etc/fstab

## fix docker issue
touch /etc/docker/daemon.json
echo "{
  \"exec-opts\": [\"native.cgroupdriver=systemd\"]
}
" > /etc/docker/daemon.json
systemctl daemon-reload
systemctl restart docker
systemctl restart kubelet


# echo "REBOOTING..."
# reboot