ARG version=1.8.27
FROM ethereum/client-go:v${version}
RUN apk add --no-cache bash expect
COPY entrypoint.sh wallet.exp /
ENTRYPOINT [ "./entrypoint.sh" ]
