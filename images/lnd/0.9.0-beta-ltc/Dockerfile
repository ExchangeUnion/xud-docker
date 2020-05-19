FROM golang:1.14-alpine3.11 as builder
RUN apk add --no-cache bash git make gcc musl-dev
RUN git clone -b v0.9.0-beta https://github.com/ltcsuite/lnd $GOPATH/src/github.com/ltcsuite/lnd
WORKDIR $GOPATH/src/github.com/ltcsuite/lnd
ADD patches /tmp/patches/
RUN go mod vendor
RUN patch vendor/github.com/ltcsuite/neutrino/chainsync/filtercontrol.go /tmp/patches/checkpoints.patch
RUN go install -v -mod=vendor -tags="autopilotrpc chainrpc experimental invoicesrpc routerrpc signrpc walletrpc watchtowerrpc wtclientrpc" ./cmd/lnd ./cmd/lncli

# Final stage
FROM alpine:3.11
RUN apk add --no-cache bash expect supervisor tor
COPY --from=builder /go/bin/lnd /go/bin/lncli /usr/local/bin/
COPY entrypoint.sh wait-file.sh start_tor.sh /
COPY lnd.conf /root
COPY supervisord.conf /etc/supervisor/conf.d/
COPY torrc /etc/tor/
VOLUME [ "/root/.lnd" ]
RUN mkdir -p /root/.lnd/tor
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
EXPOSE 10009 10010 10735 20735
