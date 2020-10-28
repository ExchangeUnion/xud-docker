FROM golang:1.14-alpine3.12 as builder
RUN apk add --no-cache bash git make gcc musl-dev
WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd
ADD .src .
ARG TAGS
ARG LDFLAGS
RUN go install -v -tags="$TAGS" -ldflags "$LDFLAGS" ./cmd/lnd ./cmd/lncli
RUN strip /go/bin/lnd /go/bin/lncli

# Final stage
FROM alpine:3.12
RUN apk add --no-cache bash expect supervisor tor
COPY --from=builder /go/bin/lnd /go/bin/lncli /usr/local/bin/
COPY entrypoint.sh /entrypoint.sh
COPY wait-file.sh start_tor.sh /
COPY lnd.conf /root/lnd.conf
COPY supervisord.conf /etc/supervisor/conf.d/
COPY torrc /etc/tor/
RUN mkdir -p /root/.lnd/tor
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
