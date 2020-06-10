FROM node:12-alpine3.12 AS builder
ARG REPO=ExchangeUnion/xud
ARG BRANCH=v1.0.0-beta.4
RUN apk add --no-cache git rsync bash musl-dev go python3 make g++
# This is a "hack" to automatically invalidate the cache in case there are new commits
ADD https://api.github.com/repos/$REPO/commits/$BRANCH /dev/null
RUN git clone -b $BRANCH --depth=2 https://github.com/$REPO
WORKDIR /xud
RUN npm install
RUN npm run compile
RUN npm run compile:seedutil
RUN npm prune --production
RUN rm -rf seedutil/go


FROM node:12-alpine3.12
RUN apk add --no-cache bash supervisor tor
COPY --from=builder /xud /app
COPY entrypoint.sh xud-backup.sh /app/
COPY start_tor.sh update-backup-dir.sh /
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY torrc /etc/tor/torrc
RUN ln -s /app/bin/xucli /usr/local/bin/xucli
RUN mkdir -p /root/.xud/tor
WORKDIR /app
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
EXPOSE 8887 18887 28887
