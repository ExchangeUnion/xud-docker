import json
import socket

from .Node import Node, InvalidNetwork, NodeApi, CliError


class BitcoindApiError(Exception):
    pass


class BitcoindApi(NodeApi):
    def getblockchaininfo(self):
        try:
            return json.loads(self.cli("getblockchaininfo"))
        except CliError as e:
            # error code: -28
            # error message:
            # Loading block index...
            lines = e.output.splitlines()
            if len(lines) == 3 and "error message:" in lines[1]:
                raise BitcoindApiError(lines[2].strip())
            else:
                raise BitcoindApiError(e.output)


class Bitcoind(Node[BitcoindApi]):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        if self.mode == "external":
            self.external_config = {
                "rpc_host": self.node_config["external_rpc_host"],
                "rpc_port": self.node_config["external_rpc_port"],
                "rpc_user": self.node_config["external_rpc_user"],
                "rpc_password": self.node_config["external_rpc_password"],
                "zmqpubrawblock": self.node_config["external_zmqpubrawblock"],
                "zmqpubrawtx": self.node_config["external_zmqpubrawtx"],
            }

        self.container_spec.command.extend(self.get_command())

    def get_command(self):
        command = [
            "-server",
            "-rpcuser=xu",
            "-rpcpassword=xu",
            "-disablewallet",
            "-txindex",
            "-zmqpubrawblock=tcp://0.0.0.0:28332",
            "-zmqpubrawtx=tcp://0.0.0.0:28333",
            "-logips",
            "-rpcallowip=::/0",
            "-rpcbind=0.0.0.0",
        ]
        if self.network == "testnet":
            command.append("-rpcport=18332")
            command.append("-testnet")
        elif self.network == "mainnet":
            command.append("-rpcport=8332")
        else:
            raise InvalidNetwork(self.network)
        return command

    @property
    def cli_command(self) -> str:
        return "bitcoind-cli"

    def cli_prefix(self) -> str:
        cli = f"{self.cli_command} -rpcuser=xu -rpcpassword=xu"
        if self.network == "testnet":
            cli += " -testnet"
        return cli

    def get_external_status(self):
        s = socket.socket()
        rpc_host = self.external_config["rpc_host"]
        rpc_port = self.external_config["rpc_port"]
        try:
            s.connect((rpc_host, rpc_port))
            return "Ready (connected to external)"
        except:
            self.logger.exception(f"Failed to connect to external node {rpc_host}:{rpc_port}")
            return "Unavailable (connection to external failed)"
        finally:
            s.close()

    def status(self):
        if self.mode == "external":
            return self.get_external_status()
        elif self.mode == "neutrino":
            return "Ready (connected to Neutrino)"
        elif self.mode == "light":
            return "Ready (light mode)"
        else:
            return super().status()

    def application_status(self):
        try:
            info = self.api.getblockchaininfo()
            current: int = info["blocks"]
            total: int = info["headers"]
            if current > 0 and current == total:
                return "Ready"
            else:
                if total == 0:
                    return "Syncing 0.00% (0/0)"
                else:
                    p = current / total * 100
                    if p > 0.005:
                        p = p - 0.005
                    else:
                        p = 0
                    return "Syncing %.2f%% (%d/%d)" % (p, current, total)
        except BitcoindApiError as e:
            return str(e)
        except:
            self.logger.exception("Failed to get advanced running status")
            return "Waiting for bitcoind to come up..."
