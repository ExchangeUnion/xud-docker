FROM node:lts-alpine3.12 AS builder
RUN apk add --no-cache git bash python3 make g++ python2
WORKDIR /connext
ADD .src .
RUN npm install
RUN npm run build

FROM node:lts-alpine3.12
RUN apk add --no-cache bash supervisor curl
RUN mkdir /root/.connext
COPY --from=builder /connext /app
COPY entrypoint.sh /app
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
WORKDIR /app
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
EXPOSE 5040
