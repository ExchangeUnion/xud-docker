ARG VERSION

FROM ethereum/client-go:$VERSION
RUN apk update && apk add --no-cache bash expect
RUN mkdir /root/.ethereum
COPY ropsten-peers.txt mainnet-peers.txt /root/.ethereum/
COPY entrypoint.sh wallet.exp create-account.sh /
ENTRYPOINT [ "./entrypoint.sh" ]
