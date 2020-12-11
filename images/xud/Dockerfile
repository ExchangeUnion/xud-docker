FROM node:lts-alpine3.12 AS builder
RUN apk add --no-cache git rsync bash musl-dev go python3 make g++
WORKDIR /xud
ADD .src .
ARG GIT_REVISION
RUN echo "" > parseGitCommit.js
RUN echo "export default '-$GIT_REVISION';" > lib/Version.ts
RUN npm install
RUN npm run compile
RUN npm run compile:seedutil
RUN npm prune --production
RUN rm -rf seedutil/go
RUN strip seedutil/seedutil

FROM node:lts-alpine3.12
RUN apk add --no-cache bash tor
COPY --from=builder /xud /app
COPY entrypoint.sh update-backup-dir.sh xud-backup.sh /
WORKDIR /app
RUN ln -s /app/bin/xud /usr/local/bin/xud
RUN ln -s /app/bin/xucli /usr/local/bin/xucli
ENTRYPOINT ["/entrypoint.sh"]
VOLUME [ "/root/.xud" ]
EXPOSE 8887 18887 28887
