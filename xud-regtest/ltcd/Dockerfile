FROM golang:alpine AS build-stage
RUN apk add --no-cache alpine-sdk python3
RUN git clone https://github.com/ltcsuite/ltcd $GOPATH/src/github.com/ltcsuite/ltcd
WORKDIR $GOPATH/src/github.com/ltcsuite/ltcd
RUN GO111MODULE=on go install . ./cmd/...

RUN git clone https://github.com/ltcsuite/ltcwallet $GOPATH/src/github.com/ltcsuite/ltcwallet
WORKDIR $GOPATH/src/github.com/ltcsuite/ltcwallet
RUN GO111MODULE=on go install .

WORKDIR /

COPY init.py /
RUN pip3 install pexpect
RUN mkdir /root/.ltcwallet
RUN touch /root/.ltcwallet/ltcwallet.conf
RUN python3 init.py

RUN ls /root/.ltcwallet


# Final stage
FROM alpine
RUN apk add --no-cache bash
COPY --from=build-stage /go/bin/ltcd /bin/
COPY --from=build-stage /go/bin/ltcctl /bin/
COPY --from=build-stage /go/bin/ltcwallet /bin/
COPY --from=build-stage /root/.ltcwallet/simnet/wallet.db /
COPY --from=build-stage /miningaddr /
COPY entrypoint.sh /
VOLUME [ "/root/.ltcd", "/root/.ltcwallet" ]
ENTRYPOINT [ "./entrypoint.sh" ]
EXPOSE 18556 18554
