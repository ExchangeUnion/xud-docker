# build stage
FROM node:lts-alpine AS builder
ARG version=1.0.0-alpha.11
# RUN apk add --no-cache git rsync python bash make alpine-sdk
RUN apk add --no-cache git rsync
RUN git clone -b v${version} https://github.com/ExchangeUnion/xud
WORKDIR /xud
RUN npm install
RUN npm run compile
RUN npm prune --dev

# final stage
FROM node:lts-alpine
RUN mkdir /root/.xud
VOLUME [ "/root/.xud" ]
COPY --from=builder /xud/dist /app/dist
COPY --from=builder /xud/bin  /app/bin
COPY --from=builder /xud/package.json /app/
COPY --from=builder /xud/node_modules /app/node_modules
COPY xud.conf /tmp/
COPY entrypoint.sh /app
WORKDIR /app
ENTRYPOINT ./entrypoint.sh
EXPOSE 8885 8886
