ARG NODE_VERSION

FROM node:$NODE_VERSION
RUN apk add --no-cache bash supervisor tor
RUN mkdir /root/.xud
VOLUME [ "/root/.xud" ]
COPY --from=xud-simnet /root/xud-simnet/xud/dist /app/dist
COPY --from=xud-simnet /root/xud-simnet/xud/bin  /app/bin
COPY --from=xud-simnet /root/xud-simnet/xud/package.json /app/
COPY --from=xud-simnet /root/xud-simnet/xud/node_modules /app/node_modules
COPY xud.conf /tmp/
COPY entrypoint.sh /app
RUN ln -s /app/bin/xucli /bin/xucli
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY torrc /etc/tor/torrc
RUN mkdir /root/.xud/tor
WORKDIR /app
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
EXPOSE 28885 8887
