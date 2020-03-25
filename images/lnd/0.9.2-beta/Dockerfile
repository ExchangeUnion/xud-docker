FROM golang:1.13.9-alpine3.10 as builder
RUN apk add --no-cache bash git make gcc musl-dev
RUN git clone -b v0.9.2-beta https://github.com/lightningnetwork/lnd $GOPATH/src/github.com/lightningnetwork/lnd
WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd
RUN make tags="invoicesrpc" install

# Final stage
FROM alpine:3.10
RUN apk add --no-cache bash expect supervisor tor
COPY --from=builder /go/bin/lnd /go/bin/lncli /usr/local/bin/
COPY entrypoint.sh wait-file.sh start_tor.sh /
COPY lnd.conf /root
COPY supervisord.conf /etc/supervisor/conf.d/
COPY torrc /etc/tor/
VOLUME [ "/root/.lnd" ]
RUN mkdir -p /root/.lnd/tor
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
EXPOSE 10009 9735 19735 10735 20735
