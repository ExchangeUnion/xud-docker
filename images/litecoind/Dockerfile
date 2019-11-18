ARG ALPINE_VERSION

FROM alpine:$ALPINE_VERSION as builder
ARG VERSION

RUN apk --no-cache add musl-dev g++ make autoconf automake libtool pkgconfig boost-dev libressl-dev libevent-dev zeromq-dev

WORKDIR /tmp
RUN wget https://download.oracle.com/berkeley-db/db-4.8.30.tar.gz
RUN tar -xzf db-4.8.30.tar.gz

WORKDIR /tmp/db-4.8.30/build_unix
RUN sed s/__atomic_compare_exchange/__atomic_compare_exchange_db/g -i ../dbinc/atomic.h
RUN ../dist/configure --prefix=/usr/local --enable-cxx --with-pic --disable-shared --disable-replication
RUN make -j$(nproc)
RUN make install

WORKDIR /tmp
RUN wget https://github.com/litecoin-project/litecoin/archive/v$VERSION.tar.gz

RUN tar -xzf v*.tar.gz
WORKDIR /tmp/litecoin-$VERSION
RUN ./autogen.sh

# https://github.com/litecoin-project/litecoin/issues/407#issuecomment-458422310
# https://wiki.musl-libc.org/functional-differences-from-glibc.html
RUN sed -i '/char\ scratchpad\[SCRYPT_SCRATCHPAD_SIZE\];/a\memset(scratchpad, 0, sizeof(scratchpad));' src/crypto/scrypt.cpp
RUN sed -i 's/char\ scratchpad\[SCRYPT_SCRATCHPAD_SIZE\];/static &/g' src/crypto/scrypt.cpp

RUN ./configure --disable-ccache --disable-tests --disable-bench --without-gui --with-daemon --with-utils --without-libs
RUN make -j$(nproc)
RUN make install

RUN strip /usr/local/bin/litecoind /usr/local/bin/litecoin-cli


FROM alpine:$ALPINE_VERSION
ARG VERSION
RUN apk --no-cache add boost-system boost-filesystem boost-chrono boost-thread libevent libressl zeromq bash
COPY --from=builder /usr/local/bin/litecoind /usr/local/bin/
COPY --from=builder /usr/local/bin/litecoin-cli /usr/local/bin/
ADD entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
EXPOSE 9332 19332 29332 29333
