FROM golang:1.15.2-alpine3.12 as builder
ADD .src github.com/ExchangeUnion/xud-docker-api-poc
WORKDIR github.com/ExchangeUnion/xud-docker-api-poc
RUN go build

FROM alpine:3.12
COPY --from=builder /go/github.com/ExchangeUnion/xud-docker-api-poc/xud-docker-api-poc /usr/local/bin/proxy
ADD entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
