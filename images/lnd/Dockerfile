ARG GOLANG_VERSION
ARG ALPINE_VERSION

FROM golang:$GOLANG_VERSION as builder
ARG VERSION
RUN apk add --no-cache bash git make
ADD download_source.sh /tmp
RUN /tmp/download_source.sh $VERSION
WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd
RUN make && make install

# Final stage
FROM alpine:$ALPINE_VERSION
RUN apk add --no-cache bash expect
COPY --from=builder /go/bin/lnd /go/bin/lncli /bin/
COPY entrypoint.sh wallet.exp unlock.exp /
VOLUME [ "/root/.lnd" ]
ENTRYPOINT [ "./entrypoint.sh" ]
EXPOSE 10009