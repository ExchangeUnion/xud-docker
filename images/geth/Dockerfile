ARG VERSION

FROM ethereum/client-go:$VERSION
RUN apk update && apk add --no-cache bash expect
COPY entrypoint.sh wallet.exp create-account.sh ropsten-peers.txt mainnet-peers.txt /
ENTRYPOINT [ "./entrypoint.sh" ]
EXPOSE 8545