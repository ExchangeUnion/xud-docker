FROM node:12-alpine3.11 AS builder
ARG REPO=ExchangeUnion/xud
ARG BRANCH=v1.0.0-beta.2
# Use pure JS implemented secp256k1 bindings
RUN apk add --no-cache git rsync bash musl-dev go python3 make g++
# This is a "hack" to automatically invalidate the cache in case there are new commits
#ADD https://api.github.com/repos/$REPO/commits/$BRANCH /dev/null
RUN git clone -b $BRANCH --depth=2 https://github.com/$REPO
WORKDIR /xud
RUN git show HEAD > git_head.txt
RUN npm install
RUN npm run compile
RUN npm run compile:seedutil
RUN npm prune --production
RUN rm -rf seedutil/go

FROM node:12-alpine3.11
RUN apk add --no-cache bash supervisor tor
RUN mkdir /root/.xud
VOLUME [ "/root/.xud" ]
COPY --from=builder /xud /app
COPY xud.conf /tmp/
COPY entrypoint.sh /app
RUN ln -s /app/bin/xucli /bin/xucli
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY torrc /etc/tor/torrc
RUN mkdir /root/.xud/tor
WORKDIR /app
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
EXPOSE 28885 8887
