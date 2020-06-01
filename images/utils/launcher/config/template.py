import re

from typing import Optional, Dict

from .options import *
from .types import PortPublish, VolumeMapping


class NodeConfig:
    def __init__(self, name: str, image: str, volumes: [str], ports: [str]):
        self.name = name
        self.image = image
        self.volumes: {VolumeMapping} = {VolumeMapping(v) for v in volumes}
        self.ports: {PortPublish} = {PortPublish(p) for p in ports}

        self.options: Dict[str, Option] = {
            "dir": DirOption(self),
            "expose-ports": ExposePortsOption(self),
        }

    def parse(self, config):
        self.options["dir"].parse(config)
        self.options["expose-ports"].parse(config)


class BitcoindConfig(NodeConfig):
    def __init__(self, name: str, image: str, volumes: [str], ports: [str],
                 mode: str,
                 external_rpc_host: Optional[str],
                 external_rpc_port: Optional[int],
                 external_rpc_user: Optional[str],
                 external_rpc_password: Optional[str],
                 external_zmqpubrawblock: Optional[str],
                 external_zmqpubrawtx: Optional[str],
                 ):
        super().__init__(name, image, volumes, ports)
        self.mode = mode
        self.external_rpc_host = external_rpc_host
        self.external_rpc_port = external_rpc_port
        self.external_rpc_user = external_rpc_user
        self.external_rpc_password = external_rpc_password
        self.external_zmqpubrawblock = external_zmqpubrawblock
        self.external_zmqpubrawtx = external_zmqpubrawtx

        self.options.update({
            "mode": ModeOption(self),
            "rpc-host": RpcHostOption(self),
            "rpc-port": RpcPortOption(self),
            "rpc-user": RpcUserOption(self),
            "rpc-password": RpcPasswordOption(self),
            "zmqpubrawblock": ZmqpubrawblockOption(self),
            "zmqpubrawtx": ZmqpubrawtxOption(self),
        })

    def parse(self, config):
        super().parse(config)
        self.options["mode"].parse(config)
        if self.mode == "external":
            self.options["rpc-host"].parse(config)
            self.options["rpc-port"].parse(config)
            self.options["rpc-user"].parse(config)
            self.options["rpc-password"].parse(config)
            self.options["zmqpubrawblock"].parse(config)
            self.options["zmqpubrawtx"].parse(config)


class LitecoindConfig(BitcoindConfig):
    pass


class GethConfig(NodeConfig):
    def __init__(self, name: str, image: str, volumes: [str], ports: [str],
                 mode: str,
                 external_rpc_host: Optional[str],
                 external_rpc_port: Optional[int],
                 infura_project_id: Optional[str],
                 infura_project_secret: Optional[str],
                 eth_provider: Optional[str],
                 ):
        super().__init__(name, image, volumes, ports)
        self.mode = mode
        self.external_rpc_host = external_rpc_host
        self.external_rpc_port = external_rpc_port
        self.infura_project_id = infura_project_id
        self.infura_project_secret = infura_project_secret
        self.eth_provider = eth_provider

        self.options.update({
            "mode": ModeOption(self),
            "rpc-host": RpcHostOption(self),
            "rpc-port": RpcPortOption(self),
            "infura-project-id": InfuraProjectIdOption(self),
            "infura-project-secret": InfuraProjectSecretOption(self),
        })

    def parse(self, config):
        self.options["ancient-chaindata-dir"].parse(config)
        self.options["mode"].parse(config)
        if self.mode == "external":
            self.options["rpc-host"].parse(config)
            self.options["rpc-port"].parse(config)
        elif self.mode == "infura":
            self.options["infura-project-id"].parse(config)
            self.options["infura-project-secret"].parse(config)


class LndConfig(NodeConfig):
    pass


class ConnextConfig(NodeConfig):
    pass


class XudConfig(NodeConfig):
    pass


nodes_config = {
    "simnet": {
        "lndbtc": LndConfig(
            name="lndbtc",
            image="exchangeunion/lnd:0.10.0-beta-simnet",
            volumes=[
                "$data_dir/lndbtc:/root/.lnd",
            ],
            ports=[],
        ),
        "lndltc": LndConfig(
            name="lndltc",
            image="exchangeunion/lnd:0.9.0-beta-ltc-simnet",
            volumes=[
                "$data_dir/lndltc:/root/.lnd",
            ],
            ports=[],
        ),
        "connext": ConnextConfig(
            name="connext",
            image="exchangeunion/connext:latest",
            volumes=[
                "$data_dir/connext:/app/connext-store",
            ],
            ports=[],
        ),
        "xud": XudConfig(
            name="xud",
            image="exchangeunion/xud:latest",
            volumes=[
                "$data_dir/xud:/root/.xud",
                "$data_dir/lndbtc:/root/.lndbtc",
                "$data_dir/lndltc:/root/.lndltc",
                "/:/mnt/hostfs"
            ],
            ports=[
                "28885",
            ],
        ),
    },
    "testnet": {
        "bitcoind": BitcoindConfig(
            name="bitcoind",
            image="exchangeunion/bitcoind:0.19.1",
            volumes=[
                "$data_dir/bitcoind:/root/.bitcoin",
            ],
            ports=[],
            mode="light",  # external, neutrino, light
            external_rpc_host="127.0.0.1",
            external_rpc_port=18332,
            external_rpc_user="xu",
            external_rpc_password="xu",
            external_zmqpubrawblock="127.0.0.1:28332",
            external_zmqpubrawtx="127.0.0.1:28333",
        ),
        "litecoind": LitecoindConfig(
            name="litecoind",
            image="exchangeunion/litecoind:0.17.1",
            volumes=[
                "$data_dir/litecoind:/root/.litecoin",
            ],
            ports=[],
            mode="light",  # external, neutrino, light
            external_rpc_host="127.0.0.1",
            external_rpc_port=19332,
            external_rpc_user="xu",
            external_rpc_password="xu",
            external_zmqpubrawblock="127.0.0.1:29332",
            external_zmqpubrawtx="127.0.0.1:29333",
        ),
        "geth": GethConfig(
            name="geth",
            image="exchangeunion/geth:1.9.14",
            volumes=[
                "$data_dir/geth:/root/.ethereum",
            ],
            ports=[],
            mode="light",  # external, infura, light
            external_rpc_host="127.0.0.1",
            external_rpc_port=8545,
            infura_project_id=None,
            infura_project_secret=None,
            eth_provider=None,
            cache=256,
        ),
        "lndbtc": LndConfig(
            name="lndbtc",
            image="exchangeunion/lnd:0.10.0-beta",
            volumes=[
                "$data_dir/lndbtc:/root/.lnd",
            ],
            ports=[],
        ),
        "lndltc": LndConfig(
            name="lndltc",
            image="exchangeunion/lnd:0.9.0-beta-ltc",
            volumes=[
                "$data_dir/lndltc:/root/.lnd",
            ],
            ports=[],
        ),
        "connext": ConnextConfig(
            name="connext",
            image="exchangeunion/connext:latest",
            volumes=[
                "$data_dir/connext:/app/connext-store",
            ],
            ports=[],
        ),
        "xud": XudConfig(
            name="xud",
            image="exchangeunion/xud:latest",
            volumes=[
                "$data_dir/xud:/root/.xud",
                "$data_dir/lndbtc:/root/.lndbtc",
                "$data_dir/lndltc:/root/.lndltc",
                "/:/mnt/hostfs",
            ],
            ports=[
                "18885"
            ],
        ),
    },
}

general_config = {
    "simnet": {
        "eth_providers": [

        ]
    },
    "testnet": {
        "eth_providers": [
            "http://eth.kilrau.com:52041",
            "http://gethxudxv2k4pv5t5a5lswq2hcv3icmj3uwg7m2n2vuykiyv77legiad.onion:8546",
        ]
    },
    "mainnet": {
        "eth_providers": [
            "http://eth.kilrau.com:41007",
            "http://gethxudxv2k4pv5t5a5lswq2hcv3icmj3uwg7m2n2vuykiyv77legiad.onion:8545"
        ]
    }
}
