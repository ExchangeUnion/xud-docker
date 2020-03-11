FROM golang:1.12-alpine3.10 as builder
RUN apk add --no-cache bash git make gcc musl-dev
RUN git clone -b v0.8.2-beta https://github.com/lightningnetwork/lnd $GOPATH/src/github.com/lightningnetwork/lnd
WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd
ENV GO111MODULE=on
ADD patches /tmp/patches/
RUN git apply /tmp/patches/limits.patch
RUN go mod vendor
RUN patch vendor/github.com/lightninglabs/neutrino/blockmanager.go /tmp/patches/neutrino.patch
RUN sed -i.bak "s/\!w.isDevEnv/w.isDevEnv/" vendor/github.com/btcsuite/btcwallet/wallet/wallet.go
RUN patch lnd.go /tmp/patches/lnd.patch
RUN go install -v -mod=vendor -tags="invoicesrpc" -ldflags "-X github.com/lightningnetwork/lnd/build.Commit=v0.8.2-beta" ./cmd/lnd ./cmd/lncli


FROM alpine:3.10
RUN apk add --no-cache bash expect supervisor tor
COPY --from=builder /go/bin/lnd /go/bin/lncli /usr/local/bin/
COPY entrypoint.sh wait-file.sh peers.sh start_tor.sh /
COPY lnd-btc.conf lnd-ltc.conf /root/
COPY supervisord.conf /etc/supervisor/conf.d/
COPY torrc /etc/tor/
VOLUME ["/root/.lnd"]
RUN mkdir -p /root/.lnd/tor
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
EXPOSE 10009
