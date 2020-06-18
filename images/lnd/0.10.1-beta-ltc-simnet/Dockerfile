FROM golang:1.13-alpine3.11 as builder
RUN apk add --no-cache bash git make gcc musl-dev
ARG VERSION=v0.10.1-beta
RUN wget https://github.com/ltcsuite/lnd/archive/$VERSION.tar.gz
ARG XUD_SIMNET_COMMIT=7d101014d8337759762dcad1e62501d7dd8ad383
RUN wget https://github.com/ExchangeUnion/xud-simnet/raw/$XUD_SIMNET_COMMIT/lndltc-$VERSION/vendor.tar.gz
RUN mkdir -p $GOPATH/src/github.com/lightningnetwork/lnd
RUN tar -xf lnd-source-$VERSION.tar.gz -C $GOPATH/src/github.com/lightningnetwork/lnd
RUN tar -xf vendor.tar.gz -C $GOPATH/src/github.com/lightningnetwork/lnd
WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd
ENV GO111MODULE=on
# patching
ADD patches /patches/
RUN git apply /patches/limits.patch
RUN git apply /patches/fundingmanager-ltc.patch
RUN patch lnd.go /patches/lnd.patch
RUN patch vendor/github.com/ltcsuite/neutrino/blockmanager.go /patches/neutrino.patch
RUN sed -i.bak "s/\!w.isDevEnv/w.isDevEnv/" vendor/github.com/ltcsuite/ltcwallet/wallet/wallet.go
# build
RUN go install -v -mod=vendor -tags="chainrpc experimental invoicesrpc routerrpc signrpc walletrpc watchtowerrpc wtclientrpc" -ldflags "-X github.com/ltcsuite/lnd/build.Commit=$VERSION-ltc-simnet" ./cmd/lnd ./cmd/lncli
RUN strip /go/bin/lnd /go/bin/lncli


FROM alpine:3.11
RUN apk add --no-cache bash tor
COPY --from=builder /go/bin/lnd /go/bin/lncli /usr/local/bin/
COPY entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
VOLUME ["/root/.lnd"]
EXPOSE 10009 10010 8080 30735
