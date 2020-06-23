FROM node:12-alpine3.11 AS builder
ARG REPO=ExchangeUnion/xud
ARG BRANCH=swaps/settle-invoice
RUN apk add --no-cache git rsync bash musl-dev go python3 make g++
RUN git clone -b $BRANCH --depth=2 https://github.com/$REPO
WORKDIR /xud
RUN npm install
RUN npm run compile
RUN npm run compile:seedutil
RUN npm prune --production
RUN rm -rf seedutil/go
RUN strip seedutil/seedutil

FROM node:12-alpine3.11
RUN apk add --no-cache bash tor
COPY --from=builder /xud /app
COPY entrypoint.sh update-backup-dir.sh xud-backup.sh /
WORKDIR /app
RUN ln -s /app/bin/xud /usr/local/bin/xud
RUN ln -s /app/bin/xucli /usr/local/bin/xucli
ENTRYPOINT ["/entrypoint.sh"]
VOLUME [ "/root/.xud" ]
EXPOSE 8887 18887 28887
