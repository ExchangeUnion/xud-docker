FROM node:14-alpine3.11 as builder
ARG REPO=ExchangeUnion/xud-webui-poc
ARG BRANCH=master
RUN apk --no-cache add git
RUN git clone -b $BRANCH https://github.com/$REPO /src
WORKDIR /src
RUN git pull origin $BRANCH
RUN yarn install
RUN yarn build

FROM nginx:1.19.0-alpine
COPY --from=builder /src/build/ /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
RUN mkdir -p /var/nginx/logs
