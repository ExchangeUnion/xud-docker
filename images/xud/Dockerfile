FROM node:12.18.3-alpine3.12 AS builder
RUN apk add --no-cache git rsync bash musl-dev go python3 make g++ curl
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
RUN curl -sfL https://install.goreleaser.com/github.com/tj/node-prune.sh | bash -s -- -b /usr/local/bin
RUN node-prune

FROM node:12.18.3-alpine3.12
RUN npm install pm2 -g
COPY --from=builder /xud /app
RUN ln -s /app/bin/xud /usr/local/bin/xud
RUN ln -s /app/bin/xucli /usr/local/bin/xucli
RUN ln -s /app/bin/xud-backup /usr/local/bin/xud-backup
ADD process.json /
ENTRYPOINT ["pm2-runtime", "start", "process.json"]
