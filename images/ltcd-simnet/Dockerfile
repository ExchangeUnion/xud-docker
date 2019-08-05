ARG ALPINE_VERSION

FROM alpine:$ALPINE_VERSION
RUN apk add --no-cache bash
COPY --from=xud-simnet /root/xud-simnet/go/bin/ltcd /root/xud-simnet/go/bin/ltcctl /usr/local/bin/
COPY entrypoint.sh /
ENTRYPOINT [ "/entrypoint.sh" ]
VOLUME [ "/root/.ltcd" ]
EXPOSE 18556
