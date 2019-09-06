ARG GOLANG_VERSION
ARG ALPINE_VERSION

FROM golang:$GOLANG_VERSION as builder
ARG REPO
ARG BRANCH
RUN apk add --no-cache bash git make
RUN git clone -b ${BRANCH} https://github.com/${REPO} $GOPATH/src/github.com/lightningnetwork/lnd
WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd
RUN make tags="invoicesrpc" install

# Final stage
FROM alpine:$ALPINE_VERSION
RUN apk add --no-cache bash expect supervisor tor
COPY --from=builder /go/bin/lnd /go/bin/lncli /usr/local/bin/
COPY entrypoint.sh wallet.exp unlock.exp unlocker.sh wait-file.sh /
COPY lnd-btc.conf lnd-ltc.conf /root/
COPY supervisord.conf /etc/supervisor/conf.d/
COPY torrc /etc/tor/
VOLUME [ "/root/.lnd" ]
RUN mkdir /root/.lnd/tor
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
EXPOSE 10009
