ARG GOLANG_VERSION
ARG ALPINE_VERSION

FROM golang:$GOLANG_VERSION as builder
ARG REPO
ARG BRANCH
RUN apk add --no-cache bash git make
RUN git clone -b ${BRANCH} https://github.com/${REPO} $GOPATH/src/github.com/lightningnetwork/lnd
WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd
RUN make tags="invoicesrpc" install

FROM alpine:$ALPINE_VERSION
RUN apk add --no-cache bash
COPY --from=builder /go/bin/lnd /go/bin/lncli /usr/local/bin/
COPY lnd-btc.conf lnd-ltc.conf /tmp/
COPY entrypoint.sh /
VOLUME [ "/root/.lnd" ]
ENTRYPOINT ["./entrypoint.sh"]
EXPOSE 10009
