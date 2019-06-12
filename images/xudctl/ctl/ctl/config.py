network = "testnet"
host = "localhost"


class ServiceConfig:
    def __init__(self, address, datadir):
        self.address = address
        self.datadir = datadir


bitcoind = ServiceConfig("http://xu:xu@$host:18332", "$datadir/bitcoind")
litecoind = ServiceConfig("http://xu:xu@$host:19332", "$datadir/litecoind")
lndbtc = ServiceConfig("grpc://$host:10009", "$datadir/lndbtc")
lndltc = ServiceConfig("grpc://$host:20009", "$datadir/lndltc")
geth = ServiceConfig("http://$host:8545", "$datadir/geth")
raiden = ServiceConfig("http://$host:5001", "$datadir/raiden")
xud = ServiceConfig("http://$host:8886", "$datadir/xud")

