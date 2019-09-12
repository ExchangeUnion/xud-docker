#!/bin/bash

set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <test-script> [args...]"
    exit 1
fi

TIMESTAMP=$(date +%s)
HOST="xud-docker-$TIMESTAMP-$USER"
if [[ -n $NAME_SUFFIX ]]; then
    HOST="$HOST-$NAME_SUFFIX"
fi
SSHCONFIG="$HOST"
TESTSCRIPT="$1"
ARGS="$@"
shift 1

cat startup.template | sed "s/<user>/$USER/g" | sed "s|<pubkey>|$(cat ~/.ssh/id_rsa.pub)|g" >startup.sh

IP=$(gcloud --format 'get(networkInterfaces[0].accessConfigs[0].natIP)' compute instances create "$HOST" \
    --image-family=ubuntu-1804-lts \
    --image-project=ubuntu-os-cloud \
    --machine-type="$MACHINE_TYPE" \
    --boot-disk-size="$DISK_SIZE" \
    --boot-disk-type=pd-ssd \
    --metadata-from-file startup-script=startup.sh)

cat <<EOF >"$SSHCONFIG"
Host $HOST
User yy
HostName $IP
ServerAliveInterval 1
ServerAliveCountMax 1
UserKnownHostsFile /dev/null
StrictHostKeyChecking no
LogLevel ERROR
# $ARGS
EOF

_ssh() {
    ssh -F $SSHCONFIG "$@"
}

_scp() {
    scp -F $SSHCONFIG "$@"
}

echo "Waiting for $HOST [$IP] to be ready"

while ! _ssh "$HOST" "which docker && which docker-compose" >/dev/null 2>&1; do
    echo -n "."
    sleep 1
done

echo ""

_scp "$TESTSCRIPT" "$HOST":~
_ssh "$HOST" "chmod u+x $TESTSCRIPT"
_ssh "$HOST" -t "NETWORK=$NETWORK tmux new -d && tmux send-keys './$TESTSCRIPT $@' ENTER && tmux attach"
