FROM golang:1.15-alpine3.12 as builder
WORKDIR github.com/ExchangeUnion/xud-docker-api-poc
COPY .src/go.mod .
COPY .src/go.sum .
RUN go mod download
ADD .src .
RUN go build ./cmd/proxy

FROM alpine:3.12
COPY --from=builder /go/github.com/ExchangeUnion/xud-docker-api-poc/proxy /usr/local/bin/proxy
COPY --from=builder /go/github.com/ExchangeUnion/xud-docker-api-poc/cmd/proxy/cert.sh .
RUN apk add --update openssl
ADD entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
