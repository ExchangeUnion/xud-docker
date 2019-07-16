FROM alpine:3.9.3 as builder
ARG version

COPY --from=boltz/berkeley-db /opt /opt

RUN apk update && apk upgrade
RUN apk --no-cache add \
    file \
    gnupg \
    libtool \
    chrpath \
    automake \
    libressl \
    autoconf \
    boost-dev \
    build-base \
    zeromq-dev \
    libevent-dev \
    libressl-dev \
    protobuf-dev \
    linux-headers

RUN gpg --batch --keyserver keyserver.ubuntu.com --recv-keys "90C8019E36C2E964"

ENV BITCOIN_PREFIX=/opt/bitcoin-$version

RUN wget https://bitcoin.org/bin/bitcoin-core-$version/SHA256SUMS.asc
RUN wget https://bitcoin.org/bin/bitcoin-core-$version/bitcoin-$version.tar.gz

RUN gpg --verify SHA256SUMS.asc
RUN grep " bitcoin-$version.tar.gz\$" SHA256SUMS.asc | sha256sum -c -
RUN tar -xzf *.tar.gz

WORKDIR /bitcoin-$version

RUN sed -i '/AC_PREREQ/a\AR_FLAGS=cr' src/univalue/configure.ac
RUN sed -i '/AX_PROG_CC_FOR_BUILD/a\AR_FLAGS=cr' src/secp256k1/configure.ac
RUN sed -i s:sys/fcntl.h:fcntl.h: src/compat.h

RUN ./autogen.sh
RUN ./configure LDFLAGS=-L`ls -d /opt/db*`/lib/ CPPFLAGS=-I`ls -d /opt/db*`/include/ \
    --prefix=${BITCOIN_PREFIX} \
    --mandir=/usr/share/man \
    --disable-ccache \
    --disable-tests \
    --disable-bench \
    --without-gui \
    --with-daemon \
    --with-utils \
    --with-libs

RUN make -j$(nproc)
RUN make install

RUN strip ${BITCOIN_PREFIX}/bin/bitcoind
RUN strip ${BITCOIN_PREFIX}/bin/bitcoin-tx
RUN strip ${BITCOIN_PREFIX}/bin/bitcoin-cli
#RUN strip ${BITCOIN_PREFIX}/bin/bitcoin-wallet

# Assemble the final image
FROM alpine:3.9.3
ARG version
RUN apk update && apk upgrade
RUN apk --no-cache add \
    boost \
    libzmq \
    libevent \
    libressl \
    boost-program_options
COPY --from=builder /opt/bitcoin-$version/bin /bin
ENTRYPOINT ["bitcoind"]
EXPOSE 8332 18332 28332 28333
