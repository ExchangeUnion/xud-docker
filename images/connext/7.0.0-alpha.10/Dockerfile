FROM node:14-alpine3.12 AS builder
ARG REPO=connext/rest-api-client
ARG BRANCH=master
RUN apk add --no-cache git bash python3 make g++
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN git clone -b $BRANCH --depth=2 https://github.com/$REPO /connext
WORKDIR /connext
RUN git fetch && git checkout f66093525b5f64a9dcbb1a29ebe64517bdc0698b
RUN npm install
RUN npm run build

FROM node:14-alpine3.12
RUN apk add --no-cache bash supervisor curl
RUN mkdir /root/.connext
COPY --from=builder /connext /app
COPY entrypoint.sh /app
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
WORKDIR /app
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
EXPOSE 5040
