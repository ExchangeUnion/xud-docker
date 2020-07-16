FROM golang:1.13-alpine3.11 as builder
RUN apk add --no-cache bash git make gcc musl-dev
WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd
ARG SRC_DIR
ADD $SRC_DIR .
RUN make tags="autopilotrpc chainrpc experimental invoicesrpc routerrpc signrpc walletrpc watchtowerrpc wtclientrpc" install

# Final stage
FROM alpine:3.11
RUN apk add --no-cache bash expect supervisor tor
COPY --from=builder /go/bin/lnd /go/bin/lncli /usr/local/bin/
ARG ENTRYPOINT_FILE
COPY $ENTRYPOINT_FILE /entrypoint.sh
COPY wait-file.sh start_tor.sh /
ARG LND_CONF_FILE
COPY $LND_CONF_FILE /root/lnd.conf
COPY supervisord.conf /etc/supervisor/conf.d/
COPY torrc /etc/tor/
RUN mkdir -p /root/.lnd/tor
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
