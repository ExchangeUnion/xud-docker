import argparse
import logging
import subprocess
from . import config
from .status import main as status

logging.basicConfig(level=logging.INFO)


def init_parser_with_config(parser):
    parser.add_argument("-n", "--network", type=str, default=config.network,
                        choices=['regtest', 'simnet', 'testnet', 'mainnet'])
    parser.add_argument("--bitcoind.address", type=str, default=config.bitcoind.address)
    parser.add_argument("--bitcoind.datadir", type=str, default=config.bitcoind.datadir)
    parser.add_argument("--litecoind.address", type=str, default=config.litecoind.address)
    parser.add_argument("--litecoind.datadir", type=str, default=config.litecoind.datadir)
    parser.add_argument("--lndbtc.address", type=str, default=config.lndbtc.address)
    parser.add_argument("--lndbtc.datadir", type=str, default=config.lndbtc.datadir)
    parser.add_argument("--lndltc.address", type=str, default=config.lndltc.address)
    parser.add_argument("--lndltc.datadir", type=str, default=config.lndltc.datadir)
    parser.add_argument("--geth.address", type=str, default=config.geth.address)
    parser.add_argument("--geth.datadir", type=str, default=config.geth.datadir)
    parser.add_argument("--raiden.address", type=str, default=config.raiden.address)
    parser.add_argument("--raiden.datadir", type=str, default=config.raiden.datadir)
    parser.add_argument("--xud.address", type=str, default=config.xud.address)
    parser.add_argument("--xud.datadir", type=str, default=config.xud.datadir)

    parser.add_argument("--host", type=str, default=config.host)


def update_config(args):
    config.network = args["network"]
    config.bitcoind.address = args["bitcoind.address"]
    config.bitcoind.datadir = args["bitcoind.datadir"]
    config.litecoind.address = args["litecoind.address"]
    config.litecoind.datadir = args["litecoind.datadir"]
    config.lndbtc.address = args["lndbtc.address"]
    config.lndbtc.datadir = args["lndbtc.datadir"]
    config.lndltc.address = args["lndltc.address"]
    config.lndltc.datadir = args["lndltc.datadir"]
    config.geth.address = args["geth.address"]
    config.geth.datadir = args["geth.datadir"]
    config.raiden.address = args["raiden.address"]
    config.raiden.datadir = args["raiden.datadir"]
    config.xud.address = args["xud.address"]
    config.xud.datadir = args["xud.datadir"]

    config.host = args["host"]


def main():
    parser = argparse.ArgumentParser()

    init_parser_with_config(parser)

    sub = parser.add_subparsers(dest="subparser")
    cmd_status = sub.add_parser("status")

    args = parser.parse_args()

    kwargs = vars(args)

    update_config(kwargs)

    try:
        globals()[kwargs.pop('subparser')]()
    except KeyError:
        parser.print_help()


if __name__ == '__main__':
    main()
