FROM golang:1.13-alpine3.12 as builder
RUN apk add --no-cache bash git make gcc musl-dev
WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd
ADD .src .
ARG TAGS
ARG LDFLAGS
RUN go install -v -tags="$TAGS" -ldflags "$LDFLAGS" ./cmd/lnd ./cmd/lncli
RUN strip /go/bin/lnd /go/bin/lncli

# Final stage
FROM alpine:3.12
RUN apk add --no-cache bash tor
COPY --from=builder /go/bin/lnd /go/bin/lncli /usr/local/bin/
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
