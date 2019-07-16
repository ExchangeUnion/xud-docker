FROM xud-simnet AS build

# Final stage
FROM alpine
RUN apk add --no-cache bash
COPY --from=build /root/xud-simnet/go/bin/ltcd /root/xud-simnet/go/bin/ltcctl /usr/local/bin/
COPY entrypoint.sh /
ENTRYPOINT [ "/entrypoint.sh" ]
VOLUME [ "/root/.ltcd" ]
EXPOSE 18556
