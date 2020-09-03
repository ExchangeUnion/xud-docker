FROM alpine:3.12.0
RUN apk add --no-cache tor
ENTRYPOINT ["tor"]
ADD torrc /etc/tor/torrc
