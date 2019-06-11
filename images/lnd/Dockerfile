FROM golang:alpine as build-stage
ARG version=0.6.1-beta-rc2
RUN apk add --no-cache alpine-sdk
RUN git clone -b v${version} https://github.com/lightningnetwork/lnd $GOPATH/src/github.com/lightningnetwork/lnd
WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd
RUN make && make install

# Final stage
FROM alpine
RUN apk add --no-cache bash expect
COPY --from=build-stage /go/bin/lnd /go/bin/lncli /bin/
COPY entrypoint.sh wallet.exp unlock.exp /
VOLUME [ "/root/.lnd" ]
ENTRYPOINT [ "./entrypoint.sh" ]
EXPOSE 10009