# build stage
FROM node:lts-alpine AS builder
ARG branch=master
# RUN apk add --no-cache git rsync python bash make alpine-sdk
RUN apk add --no-cache git rsync
RUN git clone -b ${branch} https://github.com/ExchangeUnion/xud
WORKDIR /xud
RUN npm install
RUN npm run compile
RUN npm prune --dev

# final stage
FROM node:lts-alpine
RUN apk add --no-cache bash
RUN mkdir /root/.xud
VOLUME [ "/root/.xud" ]
COPY --from=builder /xud/dist /app/dist
COPY --from=builder /xud/bin  /app/bin
COPY --from=builder /xud/package.json /app/
COPY --from=builder /xud/node_modules /app/node_modules
COPY xud.conf /tmp/
COPY entrypoint.sh /app
RUN ln -s /app/bin/xucli /bin/xucli
WORKDIR /app
ENTRYPOINT ./entrypoint.sh
EXPOSE 8885 8886
