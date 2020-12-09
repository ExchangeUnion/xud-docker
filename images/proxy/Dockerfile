FROM golang:1.15-alpine3.12 as builder
RUN apk --no-cache add make
WORKDIR /src
ADD .src .
WORKDIR /src/backend
RUN go mod download
RUN make

FROM node:14-alpine3.12 AS ui-builder
WORKDIR /src
ADD .src .
WORKDIR /src/frontend
RUN yarn install
RUN yarn build

FROM alpine:3.12
RUN apk add --update openssl bash docker-cli
COPY --from=builder /src/backend/proxy /usr/local/bin/proxy
COPY --from=ui-builder /src/frontend/build ./ui
ADD entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
