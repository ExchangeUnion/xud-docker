ARG VERSION

FROM ethereum/client-go:$VERSION

RUN apk update && apk add --no-cache bash expect

COPY entrypoint.sh wallet.exp create-account.sh /

ENTRYPOINT [ "./entrypoint.sh" ]
