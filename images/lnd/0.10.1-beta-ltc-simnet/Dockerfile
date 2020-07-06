FROM golang:1.14-alpine3.12 as builder
RUN apk add --no-cache bash git make gcc musl-dev
ARG VERSION=v0.10.1-beta
RUN wget https://github.com/ltcsuite/lnd/archive/$VERSION.tar.gz
RUN mkdir -p $GOPATH/src/github.com/ltcsuite/lnd
RUN tar -xf $VERSION.tar.gz -C $GOPATH/src/github.com/ltcsuite/lnd
WORKDIR $GOPATH/src/github.com/ltcsuite/lnd
RUN mv lnd-0.10.1-beta/* .
RUN go mod vendor
ENV GO111MODULE=on
# patching
RUN apk add --no-cache patch
ADD patches /patches/
RUN git apply /patches/limits.patch
RUN git apply /patches/fundingmanager-ltc.patch
RUN patch lnd.go /patches/lnd.patch
RUN patch vendor/github.com/ltcsuite/neutrino/blockmanager.go /patches/neutrino.patch
RUN sed -i.bak "s/\!w.isDevEnv/w.isDevEnv/" vendor/github.com/ltcsuite/ltcwallet/wallet/wallet.go
# build
RUN go install -v -mod=vendor -tags="chainrpc experimental invoicesrpc routerrpc signrpc walletrpc watchtowerrpc wtclientrpc" -ldflags "-X github.com/ltcsuite/lnd/build.Commit=$VERSION-ltc-simnet" ./cmd/lnd ./cmd/lncli
RUN strip /go/bin/lnd /go/bin/lncli


FROM alpine:3.12
RUN apk add --no-cache bash tor
COPY --from=builder /go/bin/lnd /go/bin/lncli /usr/local/bin/
COPY entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
VOLUME ["/root/.lnd"]
EXPOSE 10009 10010 8080 30735
