FROM golang:1.14-alpine3.12 as builder
RUN apk add --no-cache bash git make gcc libc-dev
WORKDIR $GOPATH/src/github.com/BoltzExchange/boltz-lnd
ADD .src .
RUN go mod vendor
RUN make install

# Final stage
FROM alpine:3.12
RUN apk add --no-cache bash expect supervisor tor
COPY --from=builder /go/bin/boltzd /go/bin/boltzcli /usr/local/bin/
COPY --from=builder /go/src/github.com/BoltzExchange/boltz-lnd/example/config.toml /sample-config.toml
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /
COPY wrapper.sh /usr/bin/wrapper

ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

EXPOSE 9002 9003
