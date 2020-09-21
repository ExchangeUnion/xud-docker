from .base import Node


class Proxy(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        command = [
            "--xud.rpchost=xud",
            "--xud.rpccert=/root/.xud/tls.cert",
        ]
        if self.network == "simnet":
            command.append("--xud.rpcport=28886")
        elif self.network == "testnet":
            command.append("--xud.rpcport=18886")
        elif self.network == "mainnet":
            command.append("--xud.rpcport=8886")

        self.container_spec.command.extend(command)

    def status(self):
        return "Ready"
