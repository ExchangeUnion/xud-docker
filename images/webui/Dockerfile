FROM node:14-alpine3.12 as builder
RUN apk --no-cache add git

WORKDIR /src
ADD .src .

WORKDIR /src/frontend
RUN yarn install
RUN yarn build

WORKDIR /src/backend
RUN yarn install
RUN apk --no-cache add bash
RUN yarn build


FROM node:14-alpine3.12
COPY --from=builder /src/backend/node_modules /app/node_modules
COPY --from=builder /src/backend/dist /app/dist
COPY --from=builder /src/backend/bin /app/bin
COPY --from=builder /src/frontend/build /app/public
COPY entrypoint.sh /
WORKDIR /app
RUN apk --no-cache add supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
