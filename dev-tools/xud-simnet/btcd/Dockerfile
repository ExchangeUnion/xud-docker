FROM golang:alpine AS build-stage
RUN apk add --no-cache alpine-sdk
RUN git clone https://github.com/ExchangeUnion/btcd $GOPATH/src/github.com/btcsuite/btcd
WORKDIR $GOPATH/src/github.com/btcsuite/btcd
RUN GO111MODULE=on go install . ./cmd/...

# Final stage
FROM alpine
COPY --from=build-stage /go/bin/btcd /bin/
COPY --from=build-stage /go/bin/btcctl /bin/
COPY entrypoint.sh /
VOLUME [ "/root/.btcd" ]
ENTRYPOINT [ "./entrypoint.sh" ]
EXPOSE 18556
