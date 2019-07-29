ARG GOLANG_VERSION
ARG ALPINE_VERSION

FROM golang:$GOLANG_VERSION AS builder
ARG VERSION
RUN apk add --no-cache bash git
ADD download_source.sh /tmp
RUN /tmp/download_source.sh $VERSION
WORKDIR $GOPATH/src/github.com/btcsuite/btcd
RUN GO111MODULE=on go install . ./cmd/...

# Final stage
FROM alpine:$ALPINE_VERSION
COPY --from=builder /go/bin/btcd /go/bin/btcctl /bin/
COPY entrypoint.sh /
ENTRYPOINT [ "./entrypoint.sh" ]
VOLUME [ "/root/.btcd" ]
EXPOSE 18556
