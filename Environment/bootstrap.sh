#!/usr/bin/env bash

apt -y update
apt -y upgrade

## Install English language packs
#apt -y install language-pack-en
#
## Set system-wide language to English
#update-locale LANG=en_US.UTF-8 LANGUAGE=en_US.UTF-8 LC_MESSAGES=POSIX
#
## Set keyboard type and layout to English
#setxkbmap -model pc105 -layout us
## Set keyboard layout to English
#DEBIAN_FRONTEND=noninteractive apt -y install console-data keyboard-configuration
##sudo DEBIAN_FRONTEND=noninteractive apt-get -y install console-data keyboard-configuration
## Set the default keyboard layout to English
##echo "setxkbmap -layout us" >> /etc/profile
#echo "setxkbmap -layout us" | sudo tee -a /etc/profile
#
##echo "setxkbmap -option ''" >>  /etc/profile
#echo "setxkbmap -option ''" | sudo tee -a  /etc/profile

# To set the guest OS timezone to Eastern Time Zone
#sudo timedatectl set-timezone America/New_York

# Enable download updates and install third-party software
#sudo sed -i 's/^#\(.*universe\)$/\1/g' /etc/apt/sources.list
#sudo sed -i 's/^#\(.*multiverse\)$/\1/g' /etc/apt/sources.list
#sudo apt -y update
#sudo apt -y upgrade
#sudo apt -y install ubuntu-restricted-extras

# Replace "username" and "password" with the desired username and password
#sudo useradd -m -s /bin/bash elena
##sudo echo "username:password" | sudo chpasswd
#sudo chpasswd < password_file

# Log out and log back in to see the changes take effect
#echo "Please log out and log back in to see the changes take effect."

#install editor
apt update -y && apt install -y nano

#install git
apt install -y git

#install python 3 package manager
apt install -y python3-dev python3-pip

#install various networking utilities
apt install -y net-tools dnsutils iputils-ping iputils-tracepath iputils-arping iputils-clockdiff inetutils-traceroute

#install zeromq
sudo -H python3 -m pip install --upgrade pyzmq

#install mininet
mkdir ~/Apps
cd ~/Apps

git clone https://github.com/mininet/mininet
./mininet/util/install.sh -a

#install protobuf
#apt install -y protobuf-compiler
#apt install -y curl
#curl -LO https://github.com/protocolbuffers/protobuf/releases/download/v21.12/protoc-21.12-linux-x86_64.zip
#unzip protoc-21.12-linux-x86_64.zip -d $HOME/.local
#export PATH="$PATH:$HOME/.local/bin"

#install emacs
#apt -y install emacs
echo "alias cls='clear'" >> ~/.bashrc
source ~/.bashrc






