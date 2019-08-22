ARG ALPINE_VERSION

FROM alpine:$ALPINE_VERSION
RUN apk add --no-cache tor
COPY torrc /etc/tor/
VOLUME ["/root/.tor"]
ENTRYPOINT ["tor"]
EXPOSE 9050
