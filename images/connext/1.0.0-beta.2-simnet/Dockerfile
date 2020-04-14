FROM node:12-alpine3.11 AS builder
ARG REPO=ConnextProject/rest-api-client
ARG BRANCH=master
# Use pure JS implemented secp256k1 bindings
RUN apk add --no-cache git bash
# This is a "hack" to automatically invalidate the cache in case there are new commits
ADD https://api.github.com/repos/$REPO/commits/$BRANCH /dev/null
RUN git clone -b $BRANCH --depth=2 https://github.com/$REPO /connext
WORKDIR /connext
RUN npm install
RUN npm run build

FROM node:12-alpine3.11
RUN apk add --no-cache bash supervisor curl
RUN mkdir /root/.connext
VOLUME [ "/root/.connext" ]
COPY --from=builder /connext /app
COPY entrypoint.sh /app
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
WORKDIR /app
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
EXPOSE 5040
