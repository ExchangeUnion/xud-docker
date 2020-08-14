from .PortPublish import PortPublish


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
        },
        "geth": {
            "name": "geth",
            "image": "exchangeunion/geth:1.9.19",
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
        },
        "lndbtc": {
            "name": "lndbtc",
            "image": "exchangeunion/lndbtc:0.10.2-beta",
            "volumes": [
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
        },
        "lndltc": {
            "name": "lndltc",
            "image": "exchangeunion/lndltc:0.10.1-beta",
            "volumes": [
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
        },
        "connext": {
            "name": "connext",
            "image": "exchangeunion/connext:1.3.0",
            "volumes": [
                {
                    "host": "$data_dir/connext",
                    "container": "/app/connext-store",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
        },
        "arby": {
            "name": "arby",
            "image": "exchangeunion/arby:1.1.5",
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
        },
        "boltz": {
            "name": "boltz",
            "image": "exchangeunion/boltz:1.1.0",
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
            "disabled": True,
        },
        "xud": {
            "name": "xud",
            "image": "exchangeunion/xud:1.0.0-beta.8",
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
