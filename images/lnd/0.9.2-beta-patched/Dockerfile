FROM golang:1.13-alpine3.10 as builder
RUN apk add --no-cache bash git make gcc musl-dev
ARG VERSION=v0.9.2-beta
RUN wget https://github.com/lightningnetwork/lnd/releases/download/$VERSION/lnd-source-$VERSION.tar.gz
RUN wget https://github.com/lightningnetwork/lnd/releases/download/$VERSION/vendor.tar.gz
RUN mkdir -p $GOPATH/src/github.com/lightningnetwork/lnd
RUN tar -xf lnd-source-$VERSION.tar.gz -C $GOPATH/src/github.com/lightningnetwork/lnd
RUN tar -xf vendor.tar.gz -C $GOPATH/src/github.com/lightningnetwork/lnd
WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd
ENV GO111MODULE=on
# patching
ADD patches /patches/
RUN git apply /patches/limits.patch
RUN git apply /patches/fundingmanager-btc.patch
RUN patch lnd.go /patches/lnd.patch
RUN patch vendor/github.com/lightninglabs/neutrino/blockmanager.go /patches/neutrino.patch
RUN sed -i.bak "s/\!w.isDevEnv/w.isDevEnv/" vendor/github.com/btcsuite/btcwallet/wallet/wallet.go
# build
RUN go install -v -mod=vendor -tags="invoicesrpc" -ldflags "-X github.com/lightningnetwork/lnd/build.Commit=$VERSION-patched" ./cmd/lnd ./cmd/lncli
RUN strip /go/bin/lnd /go/bin/lncli


FROM alpine:3.10
RUN apk add --no-cache bash tor
COPY --from=builder /go/bin/lnd /go/bin/lncli /usr/local/bin/
COPY entrypoint.sh rpc.cert /
ENTRYPOINT ["/entrypoint.sh"]
VOLUME ["/root/.lnd"]
EXPOSE 10009 10010 8080 29735
