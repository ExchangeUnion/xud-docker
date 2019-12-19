FROM node:lts-alpine
RUN apk add --no-cache git bash make python3 python3-dev python go rsync musl-dev libffi-dev patch
ADD xud-simnet /root/xud-simnet
WORKDIR /root/xud-simnet
RUN scripts/xud-simnet-install
ADD install-raiden.sh /tmp
WORKDIR /tmp
RUN ./install-raiden.sh
