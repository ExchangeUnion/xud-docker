#!/bin/sh

resolve()
{
    ping -c 1 -q $1 | head -1 | sed -nE 's/^PING[^(]+\(([^)]+)\).*/\1/p'
}

cp /tmp/xud.conf ~/.xud

hn="$(hostname)"
echo $hn
n="${hn:3}"
echo $n

if [ -z "$n" ]; then 
    insid="0"
else 
    insid="$n"
fi

sed -i "s/<instance_id>/$insid/g" ~/.xud/xud.conf
sed -i "s/<network>/$NETWORK/g" ~/.xud/xud.conf

cat ~/.xud/xud.conf

ln -sf /app/bin/xucli /bin/xucli

./bin/xud $@