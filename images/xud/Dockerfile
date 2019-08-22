ARG NODE_VERSION

FROM node:$NODE_VERSION AS builder
ARG REPO
ARG BRANCH
# Use pure JS implemented secp256k1 bindings
RUN apk add --no-cache git rsync bash
# This is a "hack" to automatically invalidate the cache in case there are new commits
ADD https://api.github.com/repos/${REPO}/commits/${BRANCH} /dev/null
RUN git clone -b ${BRANCH} https://github.com/${REPO}
WORKDIR /xud
RUN git show HEAD > git_head.txt
RUN sed -Ei 's/argv.password/password1/g' lib/cli/commands/create.ts
RUN npm install
RUN npm run compile
RUN npm prune --dev

# Final stage
FROM node:$NODE_VERSION
RUN apk add --no-cache bash proxychains-ng
RUN mkdir /root/.xud
VOLUME [ "/root/.xud" ]
COPY --from=builder /xud/dist /app/dist
COPY --from=builder /xud/bin  /app/bin
COPY --from=builder /xud/package.json /app/
COPY --from=builder /xud/node_modules /app/node_modules
COPY --from=builder /xud/git_head.txt /app/
COPY xud.conf /tmp/
COPY proxychains.conf /etc/proxychains/
COPY entrypoint.sh /app
RUN ln -s /app/bin/xucli /usr/local/bin/xucli
WORKDIR /app
ENTRYPOINT ./entrypoint.sh
EXPOSE 8885 8886 8887
