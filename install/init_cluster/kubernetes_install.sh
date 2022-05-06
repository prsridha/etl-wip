#!/bin/bash

## ONLY FOR OPENSTACK
# sudo rm -rf /var/lib/etcd/member
# sudo rm -rf /var/lib/etcd/default

# disable swap again
# for some reason the cluster resets this after reboot
sudo swapoff -a
sudo systemctl daemon-reload
sudo systemctl restart docker
sudo systemctl restart kubelet

## networking
# ip4=$(/sbin/ip -o -4 addr list eno1 | awk '{print $4}' | cut -d/ -f1)
# ip4=$(hostname -I | awk '{print $1}')
ip4="10.10.1.1"
sudo echo -e "$ip4\tk8smaster" >> /etc/hosts

## Install Kubernetes - 
sudo kubeadm init --config=kubeadm-config.yaml --upload-certs | tee kubeadm-init.out
# It should display a message saying "control plane setup, you can now join a cluster ... "