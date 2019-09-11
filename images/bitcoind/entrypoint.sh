#!/bin/sh

IP="$(hostname -i)"

bitcoind -rpcbind=$IP -rpcallowip=::/0 -zmqpubrawblock=tcp://$IP:28332 -zmqpubrawtx=tcp://$IP:28333 $@
