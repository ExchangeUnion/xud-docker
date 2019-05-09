# build stage
FROM node:lts-alpine AS build-env
RUN apk add --no-cache git rsync python bash make alpine-sdk
RUN git clone https://github.com/ExchangeUnion/xud
WORKDIR /xud
RUN npm install
RUN npm run compile
RUN npm prune --dev

# final stage
FROM node:lts-alpine
RUN mkdir /root/.xud
VOLUME [ "/root/.xud" ]
COPY --from=build-env /xud/dist /app/dist
COPY --from=build-env /xud/bin  /app/bin
COPY --from=build-env /xud/package.json /app/
COPY --from=build-env /xud/node_modules /app/node_modules
COPY xud.conf /tmp/
COPY entrypoint.sh /app
WORKDIR /app
ENTRYPOINT ./entrypoint.sh
EXPOSE 8885 8886
