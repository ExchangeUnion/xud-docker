FROM node:12-alpine3.11 AS builder
ARG REPO=ExchangeUnion/xud
ARG BRANCH=master
RUN apk add --no-cache git rsync bash musl-dev go python3 make g++ xz
# This is a "hack" to automatically invalidate the cache in case there are new commits
ADD https://api.github.com/repos/$REPO/commits/$BRANCH /dev/null
RUN git clone -b $BRANCH --depth=2 https://github.com/$REPO
WORKDIR /xud
RUN npm install
RUN npm run compile
RUN npm run compile:seedutil
RUN npm prune --production
RUN rm -rf seedutil/go
RUN strip seedutil/seedutil
RUN tar -cJf /app.tar.xz .


FROM node:12-alpine3.11
RUN apk add --no-cache bash tor xz
COPY --from=builder /app.tar.xz /
COPY entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
VOLUME [ "/root/.xud" ]
EXPOSE 8887 18887 28887
