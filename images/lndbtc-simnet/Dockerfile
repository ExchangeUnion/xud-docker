FROM golang:1.13-alpine3.11 as builder
RUN apk add --no-cache bash git make gcc musl-dev
WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd
ADD .src .
RUN go mod vendor
# patching
ADD patches /patches/
RUN /patches/apply.sh
# build
ARG TAGS
ARG LDFLAGS
RUN go install -v -mod=vendor -tags="$TAGS" -ldflags "$LDFLAGS" ./cmd/lnd ./cmd/lncli
RUN strip /go/bin/lnd /go/bin/lncli


FROM alpine:3.11
RUN apk add --no-cache bash tor
COPY --from=builder /go/bin/lnd /go/bin/lncli /usr/local/bin/
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
EXPOSE 10009
