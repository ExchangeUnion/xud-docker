FROM golang:1.14-alpine3.11 as builder

ARG REPO=BoltzExchange/boltz-lnd
ARG BRANCH=v1.0.0

RUN apk add --no-cache bash git make gcc libc-dev
# This is a "hack" to automatically invalidate the cache in case there are new commits
ADD https://api.github.com/repos/$REPO/commits/$BRANCH /dev/null
RUN git clone -b $BRANCH https://github.com/$REPO $GOPATH/src/github.com/$REPO
WORKDIR $GOPATH/src/github.com/$REPO
RUN go mod vendor
RUN make install

# Final stage
FROM alpine:3.11
RUN apk add --no-cache bash expect supervisor tor
COPY --from=builder /go/bin/boltzd /go/bin/boltzcli /usr/local/bin/
COPY --from=builder /go/src/github.com/BoltzExchange/boltz-lnd/example/config.toml /sample-config.toml
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /
COPY wrapper.sh /usr/bin/wrapper

ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

EXPOSE 9002 9003
