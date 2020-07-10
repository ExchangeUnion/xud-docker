FROM golang:1.13-alpine3.11 as builder
RUN apk add --no-cache bash git make gcc musl-dev
WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd
ARG SRC_DIR
ADD $SRC_DIR .
# patching
ARG PATCHES_DIR
ADD $PATCHES_DIR /patches/
RUN git apply /patches/limits.patch
RUN git apply /patches/fundingmanager.patch
RUN patch lnd.go /patches/lnd.patch
RUN go mod vendor
RUN patch vendor/github.com/lightninglabs/neutrino/blockmanager.go /patches/neutrino.patch
RUN sed -i.bak "s/\!w.isDevEnv/w.isDevEnv/" vendor/github.com/btcsuite/btcwallet/wallet/wallet.go
# build
ARG VERSION
RUN go install -v -mod=vendor -tags="chainrpc experimental invoicesrpc routerrpc signrpc walletrpc watchtowerrpc wtclientrpc" -ldflags "-X github.com/lightningnetwork/lnd/build.Commit=$VERSION-simnet" ./cmd/lnd ./cmd/lncli
RUN strip /go/bin/lnd /go/bin/lncli


FROM alpine:3.11
RUN apk add --no-cache bash tor
COPY --from=builder /go/bin/lnd /go/bin/lncli /usr/local/bin/
COPY entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
