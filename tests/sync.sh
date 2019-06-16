#!/bin/bash

home=/home/vagrant/.xud-docker/testnet

vagrant scp ../xud.sh /home/vagrant/
vagrant scp ../init.sh $home
vagrant scp ../banner.txt $home
vagrant scp ../xud-testnet/docker-compose.yml $home
vagrant scp ../status.sh $home