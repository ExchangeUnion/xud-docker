# build stage
FROM node:lts-alpine AS builder
#RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.nju.edu.cn/' /etc/apk/repositories
#RUN npm config set registry http://172.17.0.1:7000/repository/npm/
ARG branch=master
#RUN apk add --no-cache git rsync python bash make alpine-sdk
#RUN apk add --no-cache git rsync python bash make g++
# Use pure JS implemented secp256k1 bindings
RUN apk add --no-cache git rsync
RUN git clone -b ${branch} https://github.com/ExchangeUnion/xud
WORKDIR /xud
RUN git show HEAD > git_head.txt
RUN npm install
RUN npm run compile
RUN npm prune --dev

# final stage
FROM node:lts-alpine
RUN apk add --no-cache bash
RUN mkdir /root/.xud
VOLUME [ "/root/.xud" ]
COPY --from=builder /xud/dist /app/dist
COPY --from=builder /xud/bin  /app/bin
COPY --from=builder /xud/package.json /app/
COPY --from=builder /xud/node_modules /app/node_modules
COPY --from=builder /xud/git_head.txt /app/
COPY xud.conf /tmp/
COPY entrypoint.sh /app
RUN ln -s /app/bin/xucli /bin/xucli
WORKDIR /app
ENTRYPOINT ./entrypoint.sh
EXPOSE 8885 8886 8887
