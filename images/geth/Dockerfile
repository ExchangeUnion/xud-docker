ARG VERSION

FROM ethereum/client-go:$VERSION
RUN apk add --no-cache bash
COPY entrypoint.sh ropsten-peers.txt mainnet-peers.txt /
ENTRYPOINT [ "./entrypoint.sh" ]
EXPOSE 8545