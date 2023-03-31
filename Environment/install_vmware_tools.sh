#!/bin/bash

# Install prerequisite packages
sudo apt update && sudo apt upgrade
sudo apt install -y fuse
#sudo apt install -y open-vm-tools-desktop fuse
#
## Mount the VMware Tools ISO
#sudo mkdir -p /mnt/cdrom
#sudo mount /dev/cdrom /mnt/cdrom
#
## Copy the VMware Tools installer to the tmp directory
#sudo cp /mnt/cdrom/VMwareTools*.tar.gz /tmp/
#sudo umount /mnt/cdrom
#
## Extract the installer
#cd /tmp
#sudo tar -xzvf VMwareTools*.tar.gz
#
## Run the installer
#cd vmware-tools-distrib/
#sudo ./vmware-install.pl -d
#
## Clean up
#cd /
#sudo rm -rf /tmp/vmware-tools-distrib/
#sudo rm /tmp/VMwareTools*.tar.gz
