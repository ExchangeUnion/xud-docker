FROM alpine
RUN apk add --no-cache git bash make nodejs nodejs-npm python3 python3-dev python go rsync musl-dev libffi-dev
ADD xud-simnet /root/xud-simnet
WORKDIR /root/xud-simnet
RUN scripts/xud-simnet-install
ADD install-raiden.sh patch-xud-grpc.sh /tmp/
WORKDIR /tmp
RUN ./install-raiden.sh
RUN ./patch-xud-grpc.sh
