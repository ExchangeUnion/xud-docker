import re
from ..errors import FatalError


class PortPublish:
    def __init__(self, value):
        p1 = re.compile(r"^(\d+)$")  # 8080
        p2 = re.compile(r"^(\d+):(\d+)$")  # 80:8080
        p3 = re.compile(r"^(.+):(\d+):(\d+)$")  # 127.0.0.1:80:8080

        protocol = "tcp"
        if "/" in value:
            parts = value.split("/")
            p = parts[0]
            protocol = parts[1]
            if protocol not in ["tcp", "udp", "sctp"]:
                raise FatalError("Invalid protocol: {} ({})".format(protocol, p))

        host = None
        host_port = None
        port = None

        m = p1.match(value)
        if m:
            port = int(m.group(1))
            host_port = port
        else:
            m = p2.match(value)
            if m:
                host_port = int(m.group(1))
                port = int(m.group(2))
            else:
                m = p3.match(value)
                if m:
                    host = m.group(1)
                    host_port = int(m.group(2))
                    port = int(m.group(3))
                else:
                    raise FatalError("Invalid port publish: {}".format(value))

        self.protocol = protocol
        self.host = host
        self.host_port = host_port
        self.port = port

    def __eq__(self, other):
        if not isinstance(other, PortPublish):
            return False
        if self.host != other.host:
            return False
        if self.host_port != other.host_port:
            return False
        if self.port != other.port:
            return False
        if self.protocol != other.protocol:
            return False
        return True

    def __str__(self):
        if self.host:
            host = "{}:{}".format(self.host, self.host_port)
        else:
            host = "{}".format(self.host_port)

        container = "{}".format(self.port)

        if self.protocol == "tcp":
            return "{}:{}".format(host, container)
        elif self.protocol == "udp":
            return "{}:{}/udp".format(host, container)
        elif self.protocol == "sctp":
            return "{}:{}/sctp".format(host, container)


nodes_config = {
    "simnet": {
        "lndbtc": {
            "name": "lndbtc",
            "image": "exchangeunion/lndbtc-simnet:latest",
            "volumes": [
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
        },
        "lndltc": {
            "name": "lndltc",
            "image": "exchangeunion/lndltc-simnet:latest",
            "volumes": [
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
        },
        "connext": {
            "name": "connext",
            "image": "exchangeunion/connext:latest",
            "volumes": [
                {
                    "host": "$data_dir/connext",
                    "container": "/app/connext-store",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
        },
        "arby": {
            "name": "arby",
            "image": "exchangeunion/arby:latest",
            "volumes": [
                {
                    "host": "$data_dir/arby",
                    "container": "/root/.arby",
                },
                {
                    "host": "$data_dir/xud",
                    "container": "/root/.xud",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
            "disabled": True,
            "use_local_image": False,
        },
        "webui": {
            "name": "webui",
            "image": "exchangeunion/webui:latest",
            "volumes": [
                {
                    "host": "$data_dir/xud",
                    "container": "/root/.xud",
                }
            ],
            "ports": [PortPublish("28888:8080")],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
            "disabled": True,
        },
        "proxy": {
            "name": "proxy",
            "image": "exchangeunion/proxy:latest",
            "volumes": [
                {
                    "host": "/var/run/docker.sock",
                    "container": "/var/run/docker.sock",
                },
                {
                    "host": "$logs_dir/config.sh",
                    "container": "/root/config.sh",
                },
                {
                    "host": "$data_dir/xud",
                    "container": "/root/.xud",
                },
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lndbtc",
                },
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lndltc",
                },
            ],
            "ports": [PortPublish("127.0.0.1:28889:8080")],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
            "disabled": True,
        },
        "xud": {
            "name": "xud",
            "image": "exchangeunion/xud:latest",
            "volumes": [
                {
                    "host": "$data_dir/xud",
                    "container": "/root/.xud",
                },
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lndbtc",
                },
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lndltc",
                },
                {
                    "host": "/",
                    "container": "/mnt/hostfs",
                },
            ],
            "ports": [PortPublish("28885")],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
        },
    },
    "testnet": {
        "bitcoind": {
            "name": "bitcoind",
            "image": "exchangeunion/bitcoind:latest",
            "volumes": [
                {
                    "host": "$data_dir/bitcoind",
                    "container": "/root/.bitcoin",
                }
            ],
            "ports": [],
            "mode": "light",  # external, neutrino, light
            "external_rpc_host": "127.0.0.1",
            "external_rpc_port": 18332,
            "external_rpc_user": "xu",
            "external_rpc_password": "xu",
            "external_zmqpubrawblock": "127.0.0.1:28332",
            "external_zmqpubrawtx": "127.0.0.1:28333",
            "preserve_config": False,
            "use_local_image": False,
        },
        "litecoind": {
            "name": "litecoind",
            "image": "exchangeunion/litecoind:latest",
            "volumes": [
                {
                    "host": "$data_dir/litecoind",
                    "container": "/root/.litecoin",
                }
            ],
            "ports": [],
            "mode": "light",  # external, neutrino, light
            "external_rpc_host": "127.0.0.1",
            "external_rpc_port": 19332,
            "external_rpc_user": "xu",
            "external_rpc_password": "xu",
            "external_zmqpubrawblock": "127.0.0.1:29332",
            "external_zmqpubrawtx": "127.0.0.1:29333",
            "preserve_config": False,
            "use_local_image": False,
        },
        "geth": {
            "name": "geth",
            "image": "exchangeunion/geth:latest",
            "volumes": [
                {
                    "host": "$data_dir/geth",
                    "container": "/root/.ethereum",
                }
            ],
            "ports": [],
            "mode": "light",  # external, infura, light
            "external_rpc_host": "127.0.0.1",
            "external_rpc_port": 8545,
            "infura_project_id": None,
            "infura_project_secret": None,
            "preserve_config": False,
            "eth_provider": None,
            "cache": 256,
            "use_local_image": False,
        },
        "lndbtc": {
            "name": "lndbtc",
            "image": "exchangeunion/lndbtc:latest",
            "volumes": [
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
        },
        "lndltc": {
            "name": "lndltc",
            "image": "exchangeunion/lndltc:latest",
            "volumes": [
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
        },
        "connext": {
            "name": "connext",
            "image": "exchangeunion/connext:latest",
            "volumes": [
                {
                    "host": "$data_dir/connext",
                    "container": "/app/connext-store",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
        },
        "arby": {
            "name": "arby",
            "image": "exchangeunion/arby:latest",
            "volumes": [
                {
                    "host": "$data_dir/arby",
                    "container": "/root/.arby",
                },
                {
                    "host": "$data_dir/xud",
                    "container": "/root/.xud",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
            "disabled": True,
            "use_local_image": False,
        },
        "boltz": {
            "name": "boltz",
            "image": "exchangeunion/boltz:latest",
            "volumes": [
                {
                    "host": "$data_dir/boltz",
                    "container": "/root/.boltz",
                },
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lndbtc",
                },
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lndltc",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
            "disabled": False,
            "use_local_image": False,
        },
        "webui": {
            "name": "webui",
            "image": "exchangeunion/webui:latest",
            "volumes": [
                {
                    "host": "$data_dir/xud",
                    "container": "/root/.xud",
                }
            ],
            "ports": [PortPublish("18888:8080")],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
            "disabled": True,
        },
        "proxy": {
            "name": "proxy",
            "image": "exchangeunion/proxy:latest",
            "volumes": [
                {
                    "host": "/var/run/docker.sock",
                    "container": "/var/run/docker.sock",
                },
                {
                    "host": "$logs_dir/config.sh",
                    "container": "/root/config.sh",
                },
                {
                    "host": "$data_dir/xud",
                    "container": "/root/.xud",
                },
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lndbtc",
                },
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lndltc",
                },

            ],
            "ports": [PortPublish("127.0.0.1:18889:8080")],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
            "disabled": True,
        },
        "xud": {
            "name": "xud",
            "image": "exchangeunion/xud:latest",
            "volumes": [
                {
                    "host": "$data_dir/xud",
                    "container": "/root/.xud",
                },
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lndbtc",
                },
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lndltc",
                },
                {
                    "host": "/",
                    "container": "/mnt/hostfs",
                },
            ],
            "ports": [PortPublish("18885")],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
        },
    },
    "mainnet": {
        "bitcoind": {
            "name": "bitcoind",
            "image": "exchangeunion/bitcoind:0.20.1",
            "volumes": [
                {
                    "host": "$data_dir/bitcoind",
                    "container": "/root/.bitcoin",
                }
            ],
            "ports": [],
            "mode": "light",  # external, neutrino, light
            "external_rpc_host": "127.0.0.1",
            "external_rpc_port": 8332,
            "external_rpc_user": "xu",
            "external_rpc_password": "xu",
            "external_zmqpubrawblock": "127.0.0.1:28332",
            "external_zmqpubrawtx": "127.0.0.1:28333",
            "preserve_config": False,
            "use_local_image": False,
        },
        "litecoind": {
            "name": "litecoind",
            "image": "exchangeunion/litecoind:0.18.1",
            "volumes": [
                {
                    "host": "$data_dir/litecoind",
                    "container": "/root/.litecoin",
                }
            ],
            "ports": [],
            "mode": "light",  # external, neutrino, light
            "external_rpc_host": "127.0.0.1",
            "external_rpc_port": 9332,
            "external_rpc_user": "xu",
            "external_rpc_password": "xu",
            "external_zmqpubrawblock": "127.0.0.1:29332",
            "external_zmqpubrawtx": "127.0.0.1:29333",
            "preserve_config": False,
            "use_local_image": False,
        },
        "geth": {
            "name": "geth",
            "image": "exchangeunion/geth:1.9.22",
            "volumes": [
                {
                    "host": "$data_dir/geth",
                    "container": "/root/.ethereum",
                }
            ],
            "ports": [],
            "mode": "light",  # external, infura, light
            "external_rpc_host": "127.0.0.1",
            "external_rpc_port": 8545,
            "infura_project_id": None,
            "infura_project_secret": None,
            "preserve_config": False,
            "cache": 256,
            "use_local_image": False,
        },
        "lndbtc": {
            "name": "lndbtc",
            "image": "exchangeunion/lndbtc:0.11.1-beta",
            "volumes": [
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
        },
        "lndltc": {
            "name": "lndltc",
            "image": "exchangeunion/lndltc:0.11.0-beta.rc1",
            "volumes": [
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
        },
        "connext": {
            "name": "connext",
            "image": "exchangeunion/connext:1.3.6",
            "volumes": [
                {
                    "host": "$data_dir/connext",
                    "container": "/app/connext-store",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
        },
        "arby": {
            "name": "arby",
            "image": "exchangeunion/arby:1.3.0",
            "volumes": [
                {
                    "host": "$data_dir/arby",
                    "container": "/root/.arby",
                },
                {
                    "host": "$data_dir/xud",
                    "container": "/root/.xud",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
            "disabled": True,
            "use_local_image": False,
        },
        "boltz": {
            "name": "boltz",
            "image": "exchangeunion/boltz:1.1.1",
            "volumes": [
                {
                    "host": "$data_dir/boltz",
                    "container": "/root/.boltz",
                },
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lndbtc",
                },
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lndltc",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
            "disabled": False,
            "use_local_image": False,
        },
        "webui": {
            "name": "webui",
            "image": "exchangeunion/webui:1.0.0",
            "volumes": [
                {
                    "host": "$data_dir/xud",
                    "container": "/root/.xud",
                }
            ],
            "ports": [PortPublish("8888:8080")],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
            "disabled": True,
        },
        "proxy": {
            "name": "proxy",
            "image": "exchangeunion/proxy:1.0.0",
            "volumes": [
                {
                    "host": "/var/run/docker.sock",
                    "container": "/var/run/docker.sock",
                },
                {
                    "host": "$logs_dir/config.sh",
                    "container": "/root/config.sh",
                },
                {
                    "host": "$data_dir/xud",
                    "container": "/root/.xud",
                },
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lndbtc",
                },
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lndltc",
                },
            ],
            "ports": [PortPublish("127.0.0.1:8889:8080")],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
            "disabled": True,
        },
        "xud": {
            "name": "xud",
            "image": "exchangeunion/xud:1.2.0",
            "volumes": [
                {
                    "host": "$data_dir/xud",
                    "container": "/root/.xud",
                },
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lndbtc",
                },
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lndltc",
                },
                {
                    "host": "/",
                    "container": "/mnt/hostfs",
                },
            ],
            "ports": [PortPublish("8885")],
            "mode": "native",
            "preserve_config": False,
            "use_local_image": False,
        },
    }
}

general_config = {
    "simnet": {
        "eth_providers": [

        ]
    },
    "testnet": {
        "eth_providers": [
            "http://eth.kilrau.com:52041",
            "http://michael1011.at:8546",
            "http://gethxudxv2k4pv5t5a5lswq2hcv3icmj3uwg7m2n2vuykiyv77legiad.onion:8546"
        ]
    },
    "mainnet": {
        "eth_providers": [
            "http://eth.kilrau.com:41007",
            "http://michael1011.at:8545",
            "http://gethxudxv2k4pv5t5a5lswq2hcv3icmj3uwg7m2n2vuykiyv77legiad.onion:8545"
        ]
    }
}
