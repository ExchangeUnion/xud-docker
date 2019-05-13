FROM alpine

ARG VERSION=0.17.1
ARG ARCH=x86_64
ENV FILENAME bitcoin-${VERSION}-${ARCH}-linux-gnu.tar.gz
ENV DOWNLOAD_URL https://bitcoin.org/bin/bitcoin-core-${VERSION}/${FILENAME}

RUN apk --no-cache add wget tar ca-certificates bash \
  && wget $DOWNLOAD_URL \
  && tar zxvf /$FILENAME \
  && mkdir /root/.bitcoin \
  && mv /bitcoin-${VERSION}/bin/* /usr/local/bin/ \
  && rm -rf /bitcoin-${VERSION}/ \
  && rm -rf /$FILENAME \
  && apk del wget tar ca-certificates

EXPOSE 8332 8333 18332 18333 28332 28333

ADD entrypoint.sh /bin/

ENTRYPOINT ["/entrypoint.sh"]
