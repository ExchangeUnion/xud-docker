FROM golang:alpine AS build-stage
RUN apk add --no-cache alpine-sdk python3
RUN git clone https://github.com/btcsuite/btcd $GOPATH/src/github.com/btcsuite/btcd
WORKDIR $GOPATH/src/github.com/btcsuite/btcd
RUN GO111MODULE=on go install . ./cmd/...

RUN git clone https://github.com/btcsuite/btcwallet $GOPATH/src/github.com/btcsuite/btcwallet
WORKDIR $GOPATH/src/github.com/btcsuite/btcwallet
RUN GO111MODULE=on go install .

WORKDIR /

COPY init.py /
RUN pip3 install pexpect
RUN mkdir /root/.btcwallet
RUN touch /root/.btcwallet/btcwallet.conf
RUN python3 init.py

RUN ls /root/.btcwallet


# Final stage
FROM alpine
RUN apk add --no-cache bash
COPY --from=build-stage /go/bin/btcd /bin/
COPY --from=build-stage /go/bin/btcctl /bin/
COPY --from=build-stage /go/bin/btcwallet /bin/
COPY --from=build-stage /root/.btcwallet/simnet/wallet.db /
COPY --from=build-stage /miningaddr /
COPY entrypoint.sh /
VOLUME [ "/root/.btcd", "/root/.btcwallet" ]
ENTRYPOINT [ "./entrypoint.sh" ]
EXPOSE 18556 18554
