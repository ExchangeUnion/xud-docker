FROM golang:alpine as build-stage
RUN apk add --no-cache alpine-sdk
RUN git clone -b resolver+simnet-ltcd https://github.com/ExchangeUnion/lnd.git $GOPATH/src/github.com/lightningnetwork/lnd
WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd
RUN make && make install

# Final stage
FROM alpine
RUN apk add --no-cache bash
COPY --from=build-stage /go/bin/lnd /go/bin/lncli /bin/
ADD btcd.cert data.tar.gz entrypoint.sh /
RUN mkdir /root/.lnd
ADD tls.cert tls.key /root/.lnd/
ENTRYPOINT [ "./entrypoint.sh" ]
VOLUME [ "/root/.lnd" ]
EXPOSE 10009