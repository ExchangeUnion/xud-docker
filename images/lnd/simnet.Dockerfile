FROM golang:1.13-alpine3.11 as builder
RUN apk add --no-cache bash git make gcc musl-dev
WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd
ARG SRC_DIR
ADD $SRC_DIR .
RUN go mod vendor
# patching
ARG PATCHES_DIR
ADD $PATCHES_DIR /patches/
RUN /patches/apply.sh
# build
ARG TAGS
ARG LDFLAGS
RUN go install -v -mod=vendor -tags="$TAGS" -ldflags "$LDFLAGS" ./cmd/lnd ./cmd/lncli
RUN strip /go/bin/lnd /go/bin/lncli


FROM alpine:3.11
RUN apk add --no-cache bash tor
COPY --from=builder /go/bin/lnd /go/bin/lncli /usr/local/bin/
ARG ENTRYPOINT_FILE
COPY $ENTRYPOINT_FILE /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
EXPOSE 10009
