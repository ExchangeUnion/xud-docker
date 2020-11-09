FROM alpine:3.12 as builder
RUN apk --no-cache add musl-dev g++ make autoconf automake libtool pkgconfig boost-dev libressl-dev libevent-dev zeromq-dev
WORKDIR /litecoin
ADD .src .
RUN ./autogen.sh
# https://github.com/litecoin-project/litecoin/issues/407#issuecomment-458422310
# https://wiki.musl-libc.org/functional-differences-from-glibc.html
RUN sed -i '/char\ scratchpad\[SCRYPT_SCRATCHPAD_SIZE\];/a\memset(scratchpad, 0, sizeof(scratchpad));' src/crypto/scrypt.cpp
RUN sed -i 's/char\ scratchpad\[SCRYPT_SCRATCHPAD_SIZE\];/static &/g' src/crypto/scrypt.cpp
RUN ./configure --disable-ccache --disable-tests --disable-bench --without-gui --with-daemon --with-utils --without-libs --disable-wallet
RUN make -j$(nproc)
RUN make install
RUN strip /usr/local/bin/litecoind /usr/local/bin/litecoin-cli


FROM alpine:3.12
RUN apk --no-cache add boost-system boost-filesystem boost-chrono boost-thread libevent libressl zeromq bash
COPY --from=builder /usr/local/bin/litecoind /usr/local/bin/litecoin-cli /usr/local/bin/
ADD entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
EXPOSE 9332 19332 29332 29333
