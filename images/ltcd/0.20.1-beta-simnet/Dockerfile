FROM golang:1.14-alpine3.11 as builder
RUN apk add --no-cache bash git make gcc musl-dev
RUN git clone -b v0.20.1-beta https://github.com/ltcsuite/ltcd.git $GOPATH/src/github.com/ltcsuite/ltcd
WORKDIR $GOPATH/src/github.com/ltcsuite/ltcd
ENV GO111MODULE=on
ADD patches /tmp/patches/
RUN git apply /tmp/patches/ltcd.patch
RUN go install -v . ./cmd/...


FROM alpine:3.11
RUN apk add --no-cache bash
COPY --from=builder /go/bin/ltcd /go/bin/ltcctl /usr/local/bin/
COPY entrypoint.sh /
ENTRYPOINT [ "/entrypoint.sh" ]
VOLUME [ "/root/.ltcd" ]
EXPOSE 18556
