FROM golang:1.14-alpine3.12 as builder
RUN apk add --no-cache make gcc musl-dev linux-headers git
RUN apk add --no-cache alpine-sdk
WORKDIR /go-ethereum
ADD .src .
RUN make geth

FROM alpine:3.12
RUN apk add --no-cache ca-certificates bash
COPY --from=builder /go-ethereum/build/bin/geth /usr/local/bin/
COPY entrypoint.sh rinkeby-peers.txt mainnet-peers.txt /
EXPOSE 8545 8546 8547 30303 30303/udp
ENTRYPOINT [ "./entrypoint.sh" ]
