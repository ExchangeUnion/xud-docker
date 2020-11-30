import base64
import json
from .base import Node


MAINNET = """\
[
  {
    "name": "bitcoind",
    "rpc": {
      "type": "JSON-RPC",
      "host": "bitcoind",
      "port": 8332,
      "username": "xu",
      "password": "xu"
    },
    "disabled": true,
    "mode": "light"
  },
  {
    "name": "litecoind",
    "rpc": {
      "type": "JSON-RPC",
      "host": "litecoind",
      "port": 9332,
      "username": "xu",
      "password": "xu"
    },
    "disabled": true,
    "mode": "light"
  },
  {
    "name": "geth",
    "rpc": {
      "type": "JSON-RPC",
      "host": "geth",
      "port": 8545
    },
    "disabled": true,
    "mode": "light"
  },
  {
    "name": "lndbtc",
    "rpc": {
      "type": "gRPC",
      "host": "lndbtc",
      "port": 10009,
      "tlsCert": "/root/network/data/lndbtc/tls.cert",
      "macaroon": "/root/network/data/lndbtc/data/chain/bitcoin/mainnet/readonly.macaroon"
    },
    "disabled": false
  },
  {
    "name": "lndltc",
    "rpc": {
      "type": "gRPC",
      "host": "lndltc",
      "port": 10009,
      "tlsCert": "/root/network/data/lndltc/tls.cert",
      "macaroon": "/root/network/data/lndltc/data/chain/litecoin/mainnet/readonly.macaroon"
    },
    "disabled": false
  },
  {
    "name": "connext",
    "rpc": {
      "type": "HTTP",
      "host": "connext",
      "port": 5040
    },
    "disabled": false
  },
  {
    "name": "xud",
    "rpc": {
      "type": "gRPC",
      "host": "xud",
      "port": 8886,
      "tlsCert": "/root/network/data/xud/tls.cert"
    },
    "disabled": false
  },
  {
    "name": "arby",
    "rpc": {

    },
    "disabled": true
  },
  {
    "name": "boltz",
    "rpc": {
      "type": "gRPC",
      "host": "boltz",
      "btcPort": 9002,
      "ltcPort": 9003
    },
    "disabled": false
  },
  {
    "name": "webui",
    "rpc": {

    },
    "disabled": true
  }
]
"""

TESTNET = """\
[
  {
    "name": "bitcoind",
    "rpc": {
      "type": "JSON-RPC",
      "host": "bitcoind",
      "port": 18332,
      "username": "xu",
      "password": "xu"
    },
    "disabled": true,
    "mode": "light"
  },
  {
    "name": "litecoind",
    "rpc": {
      "type": "JSON-RPC",
      "host": "litecoind",
      "port": 19332,
      "username": "xu",
      "password": "xu"
    },
    "disabled": true,
    "mode": "light"
  },
  {
    "name": "geth",
    "rpc": {
      "type": "JSON-RPC",
      "host": "geth",
      "port": 8545
    },
    "disabled": true,
    "mode": "light"
  },
  {
    "name": "lndbtc",
    "rpc": {
      "type": "gRPC",
      "host": "lndbtc",
      "port": 10009,
      "tlsCert": "/root/network/data/lndbtc/tls.cert",
      "macaroon": "/root/network/data/lndbtc/data/chain/bitcoin/testnet/readonly.macaroon"
    },
    "disabled": false
  },
  {
    "name": "lndltc",
    "rpc": {
      "type": "gRPC",
      "host": "lndltc",
      "port": 10009,
      "tlsCert": "/root/network/data/lndltc/tls.cert",
      "macaroon": "/root/network/data/lndltc/data/chain/litecoin/testnet/readonly.macaroon"
    },
    "disabled": false
  },
  {
    "name": "connext",
    "rpc": {
      "type": "HTTP",
      "host": "connext",
      "port": 5040
    },
    "disabled": false
  },
  {
    "name": "xud",
    "rpc": {
      "type": "gRPC",
      "host": "xud",
      "port": 18886,
      "tlsCert": "/root/network/data/xud/tls.cert"
    },
    "disabled": false
  },
  {
    "name": "arby",
    "rpc": {

    },
    "disabled": true
  },
  {
    "name": "boltz",
    "rpc": {
      "type": "gRPC",
      "host": "boltz",
      "btcPort": 9002,
      "ltcPort": 9003
    },
    "disabled": false
  },
  {
    "name": "webui",
    "rpc": {

    },
    "disabled": true
  }
]
"""

SIMNET = """\
[
  {
    "name": "lndbtc",
    "rpc": {
      "type": "gRPC",
      "host": "lndbtc",
      "port": 10009,
      "tlsCert": "/root/network/data/lndbtc/tls.cert",
      "macaroon": "/root/network/data/lndbtc/data/chain/bitcoin/simnet/readonly.macaroon"
    },
    "disabled": false
  },
  {
    "name": "lndltc",
    "rpc": {
      "type": "gRPC",
      "host": "lndltc",
      "port": 10009,
      "tlsCert": "/root/network/data/lndltc/tls.cert",
      "macaroon": "/root/network/data/lndltc/data/chain/litecoin/simnet/readonly.macaroon"
    },
    "disabled": false
  },
  {
    "name": "connext",
    "rpc": {
      "type": "HTTP",
      "host": "connext",
      "port": 5040
    },
    "disabled": false
  },
  {
    "name": "xud",
    "rpc": {
      "type": "gRPC",
      "host": "xud",
      "port": 28886,
      "tlsCert": "/root/network/data/xud/tls.cert"
    },
    "disabled": false
  },
  {
    "name": "arby",
    "rpc": {

    },
    "disabled": true
  }
]
"""


class Proxy(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        self.container_spec.environment.append("SERVICES=%s" % self.get_services_json())

    def get_node(self, name: str) -> Node:
        nodes = self.node_manager.nodes
        assert name in nodes
        return nodes[name]

    def get_services_json(self) -> str:
        if self.network == "mainnet":
            j = MAINNET
            services = json.loads(j)
            for s in services:
                node = s.get_node(s["name"])
                s["disabled"] = node.disabled
                s["mode"] = node.mode





        elif self.network == "testnet":
            j = TESTNET
            services = json.loads(j)
        elif self.network == "simnet":
            j = SIMNET
            services = json.loads(j)
        else:
            return ""

        base64.b64encode(j.encode())

    def status(self):
        return "Ready"
