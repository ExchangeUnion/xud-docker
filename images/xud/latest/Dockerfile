FROM node:12-alpine3.10 AS builder
ARG REPO=ExchangeUnion/xud
ARG BRANCH=v1.0.0-beta.1
# Use pure JS implemented secp256k1 bindings
RUN apk add --no-cache git python3 rsync go musl-dev xz
# This is a "hack" to automatically invalidate the cache in case there are new commits
#ADD https://api.github.com/repos/$REPO/commits/$BRANCH /dev/null
RUN git clone --depth=2 -b $BRANCH https://github.com/$REPO
WORKDIR /xud
RUN npm install
RUN npm run compile
RUN npm run compile:seedutil
RUN rm -rf seedutil/go
RUN npm prune --production
RUN strip seedutil/seedutil
RUN tar -cJf /app.tar.xz .
RUN ls -l /app.tar.xz

FROM node:12-alpine3.10
RUN apk add --no-cache xz bash tor
COPY --from=builder /app.tar.xz /
COPY entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
VOLUME [ "/root/.xud" ]
EXPOSE 8885 18885 8887
