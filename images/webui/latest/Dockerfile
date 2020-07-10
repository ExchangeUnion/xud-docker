FROM node:14-alpine as builder
RUN apk --no-cache add git

RUN git clone -b master https://github.com/ExchangeUnion/xud-webui-poc /src/frontend
WORKDIR /src/frontend
RUN git fetch && git checkout 4de619b99507ef684fca7abe1726bb53a237d320
RUN yarn install
RUN yarn build

RUN git clone -b master https://github.com/ExchangeUnion/xud-socketio /src/backend
WORKDIR /src/backend
RUN git fetch && git checkout 8648f603209f1ae8c27328b1bf5817d512e3ca2d
RUN sed -Ei 's/^.*grpc-tools.*$//g' package.json
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
RUN apk --no-cache add supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
