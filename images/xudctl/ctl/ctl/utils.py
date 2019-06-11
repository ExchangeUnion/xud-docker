import platform
import os
from .rpc.bitcoind import Bitcoind
from .rpc.lnd import Lnd
from .rpc.raiden import Raiden
from .rpc.xud import Xud
from .rpc.geth import Geth
from . import config
import re

# Hide CryptographyDeprecationWarning: encode_point has been deprecated on EllipticCurvePublicNumbers and will be removed in a future version. Please use EllipticCurvePublicKey.public_bytes to obtain both compressed and uncompressed point encoding.
#   m.add_string(self.Q_C.public_numbers().encode_point())
# Ref. https://stackoverflow.com/a/55336269/2663029
import warnings
warnings.filterwarnings(action='ignore',module='.*paramiko.*')

prefix = "XUD_DOCKER_"

HOME = prefix + "HOME"

networks = {
    "regtest": {
        "services": {}
    },
    "simnet": {
        "services": {}
    },
    "testnet": {
        "services": {}
    },
    "mainnet": {
        "services": {}
    }
}


def print_services(title, services):
    c1w = max(len(title[0]), len(max(services.keys(), key=len)))
    c2w = max(len(title[1]), len(max(services.values(), key=len)))
    c1f = '{:' + str(c1w) + "}"
    c2f = '{:' + str(c2w) + "}"

    print(("┏━━" + c1f + "━━┯━━" + c2f + "━━┓").format("━" * c1w, "━" * c2w))
    print(("┃  " + c1f + "  │  " + c2f + "  ┃").format(title[0], title[1]))

    for key, value in services.items():
        print(("┠──" + c1f + "──┼──" + c2f + "──┨").format("─" * c1w, "─" * c2w))
        print(("┃  " + c1f + "  │  " + c2f + "  ┃").format(key, value))

    print(("┗━━" + c1f + "━━┷━━" + c2f + "━━┛").format("━" * c1w, "━" * c2w))


def get_home():
    """
    :return:
    Linux
        /home/<user>/.xud-docker
    Darwin (macOS)
        /Users/<user>/Library/Application Support/XudDocker
    Windows
        C:\\Users\\<user>\\AppData\\Local\\XudDocker
    """
    if HOME in os.environ:
        return os.environ[HOME]

    if platform.system() == 'Linux':
        return os.path.expanduser("~/.xud-docker")
    elif platform.system() == 'Darwin':
        return os.path.expanduser("~/Library/Application Support/XudDocker")
    elif platform.system() == 'Windows':
        return os.path.expanduser("~/AppData/Local/XudDocker")


def load(path):
    try:
        if ":" in path:
            # client = paramiko.SSHClient()
            # client.load_system_host_keys()
            #
            # m = re.search(r'^(.+)@(.+):(.+)$', path)
            # if m is None:
            #     raise Exception("Failed to load content from " + path)
            # path = m.group(3)
            # user = m.group(1)
            # host = m.group(2)
            #
            # client.connect(host, timeout=1, username=user)
            # sftp = client.open_sftp()
            # return sftp.open(path).read()
            raise Exception("Remote loading is not supported")
        else:
            return open(path, 'rb').read()
    except FileNotFoundError:
        raise Exception("Failed to load content from " + path)


def expand(path):
    if config.host == 'localhost':
        return path
    else:
        return config.host + ":" + path


def build_service(name):
    network = config.network

    if name == 'bitcoind':
        service = Bitcoind(config.bitcoind.address)
    elif name == 'litecoind':
        service = Bitcoind(config.litecoind.address)
    elif name == 'lndbtc':
        macaroon = expand(config.lndbtc.datadir) + ('/data/chain/bitcoin/%s/admin.macaroon' % network)
        cert = expand(config.lndbtc.datadir) + '/tls.cert'
        service = Lnd(config.lndbtc.address, load(cert), load(macaroon))
    elif name == 'lndltc':
        macaroon = expand(config.lndltc.datadir) + ('/data/chain/litecoin/%s/admin.macaroon' % network)
        cert = expand(config.lndltc.datadir) + '/tls.cert'
        service = Lnd(config.lndltc.address, load(cert), load(macaroon))
    elif name == 'geth':
        service = Geth(config.geth.address)
    elif name == 'raiden':
        service = Raiden(config.raiden.address)
    elif name == 'xud':
        cert = expand(config.xud.datadir) + '/tls.cert'
        service = Xud(config.xud.address, load(cert))
    else:
        raise Exception('Unsupported service name: ' + name)

    return service


def get_service(name):
    network = config.network
    if network not in networks:
        raise Exception("Unsupported network: %s" % network)
    services = networks[network]["services"]
    if name in services:
        return services[name]

    s = build_service(name)
    services[name] = s

    return s


