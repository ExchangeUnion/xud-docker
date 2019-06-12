from .utils import get_service


def main():
    from .utils import print_services

    bitcoind = get_service('bitcoind')
    litecoind = get_service('litecoind')
    xud = get_service('xud')
    lndbtc = get_service('lndbtc')
    lndltc = get_service('lndltc')
    geth = get_service('geth')
    raiden = get_service('raiden')

    title = ["SERVICE", "STATUS"]

    services = {
        "btc": bitcoind.status,
        "ltc": litecoind.status,
        "eth": geth.status,
        "lndbtc": lndbtc.status,
        "lndltc": lndltc.status,
        "raiden": raiden.status,
        "xud": xud.status,
    }

    print_services(title, services)




