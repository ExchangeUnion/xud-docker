FROM node:12-alpine3.11 AS builder
ARG REPO=ExchangeUnion/market-maker-tools
ARG BRANCH=master
RUN apk add --no-cache git bash
RUN git clone -b $BRANCH https://github.com/$REPO /arby
WORKDIR /arby
RUN git fetch && git checkout 22a3f5135263ab3532b9089de0c4ce910c77b8d3
RUN npm install

FROM node:12-alpine3.11
RUN apk add --no-cache bash supervisor curl rsync
RUN mkdir /root/.arby
VOLUME [ "/root/.arby" ]
COPY --from=builder /arby /app
COPY entrypoint.sh /app
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
WORKDIR /app
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
