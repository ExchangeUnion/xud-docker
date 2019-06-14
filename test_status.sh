#!/bin/bash

if lsof -i:2222; then
	scp -P 2222 status.sh vagrant@localhost:~/.xud-docker/testnet
	ssh vagrant@localhost -p 2222 'cd ~/.xud-docker/testnet && ./status.sh'
else
	cp status.sh ~/.xud-docker/testnet
	cd ~/.xud-docker/testnet && ./status.sh
fi
