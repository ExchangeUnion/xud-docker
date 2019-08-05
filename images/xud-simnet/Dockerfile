ARG NODE_VERSION

FROM node:$NODE_VERSION
RUN apk add --no-cache bash
RUN mkdir /root/.xud
VOLUME [ "/root/.xud" ]
COPY --from=xud-simnet /root/xud-simnet/xud/dist /app/dist
COPY --from=xud-simnet /root/xud-simnet/xud/bin  /app/bin
COPY --from=xud-simnet /root/xud-simnet/xud/package.json /app/
COPY --from=xud-simnet /root/xud-simnet/xud/node_modules /app/node_modules
COPY xud.conf /tmp/
COPY entrypoint.sh /app
RUN ln -s /app/bin/xucli /bin/xucli
WORKDIR /app
ENTRYPOINT ./entrypoint.sh
EXPOSE 8885 8886 8887