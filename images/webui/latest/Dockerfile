FROM node:14-alpine as builder
RUN apk --no-cache add git

RUN git clone -b socketio https://github.com/ExchangeUnion/xud-webui-poc /src/frontend
WORKDIR /src/frontend
RUN git fetch && git checkout b1f1083d
RUN yarn install
RUN yarn build

RUN git clone -b dev https://github.com/ExchangeUnion/xud-socketio /src/backend
WORKDIR /src/backend
RUN git fetch && git checkout 186cbb38
RUN yarn install
RUN apk --no-cache add bash
RUN yarn build


FROM node:14-alpine
COPY --from=builder /src/backend/node_modules /app/node_modules
COPY --from=builder /src/backend/dist /app/dist
COPY --from=builder /src/backend/bin /app/bin
COPY --from=builder /src/frontend/build /app/public
COPY entrypoint.sh /
WORKDIR /app
ENTRYPOINT ["/entrypoint.sh"]
