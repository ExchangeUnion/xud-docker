#!/bin/bash

set -euo pipefail

host="10.0.2.2"
nexus="$host:7000"
nexus_docker="$host:7001"

# Install docker-ce
# https://docs.docker.com/install/linux/docker-ce/ubuntu/
# Vagrant run this script as root
echo "apt_preserve_sources_list: true" >> /etc/cloud/cloud.cfg
sed -Ei "s|archive.ubuntu.com/ubuntu|$nexus/repository/ubuntu-16-archive|g;s|security.ubuntu.com/ubuntu|$nexus/repository/ubuntu-16-security|g" /etc/apt/sources.list
apt-get update
# No need to install apt-transport-https, ca-certificates, curl, software-properties-common as the official tutorial said
apt-get install -y gnupg-agent
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
apt-key fingerprint 0EBFCD88
# https://download.docker.com/linux/ubuntu
add-apt-repository "deb [arch=amd64] http://$nexus/repository/ubuntu-16-docker $(lsb_release -cs) stable"
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io
usermod -aG docker vagrant

# Install docker-compose
# https://docs.docker.com/compose/install/
curl -sL "https://github.com/docker/compose/releases/download/1.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

cat <<EOF > /etc/docker/daemon.json
{
	"insecure-registries": [
		"$nexus_docker"
	],
	"disable-legacy-registry": true,
	"registry-mirrors": [
		"http://$nexus_docker"
	]
}
EOF

systemctl restart docker
