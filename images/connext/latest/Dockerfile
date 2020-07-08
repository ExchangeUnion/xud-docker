FROM node:12-alpine3.11 AS builder
ARG REPO=connext/rest-api-client
ARG BRANCH=master
RUN apk add --no-cache git bash python3 make g++ python
# This is a "hack" to automatically invalidate the cache in case there are new commits
ADD https://api.github.com/repos/$REPO/commits/$BRANCH /dev/null
RUN git clone -b $BRANCH https://github.com/$REPO /connext
WORKDIR /connext
# lock connext container down to specific commit hash
RUN git checkout fe1876a0411e0b9928825ae51104e16a9fd7b787
RUN npm install
RUN npm run build

FROM node:12-alpine3.11
RUN apk add --no-cache bash supervisor curl
RUN mkdir /root/.connext
COPY --from=builder /connext /app
COPY entrypoint.sh /app
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
WORKDIR /app
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
EXPOSE 5040
