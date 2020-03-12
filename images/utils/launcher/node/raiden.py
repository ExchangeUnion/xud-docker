from .base import Node, CliBackend, CliError
import json


class RaidenApiError(Exception):
    pass


class RaidenApi:
    def __init__(self, backend):
        self._backend = backend

    def get_tokens(self):
        try:
            return json.loads(self._backend["http://localhost:5001/api/v1/tokens"]())
        except CliError as e:
            raise RaidenApiError(f"{e.exit_code}|{e.output!r}")


class Raiden(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        command = self.get_command()
        environment = self.get_environment()

        self.container_spec.command.extend(command)
        self.container_spec.environment.extend(environment)

        self._cli = "curl -s"
        self.api = RaidenApi(CliBackend(self.client, self.container_name, self._logger, self._cli))

    def get_command(self):
        command = []
        if self.network != "simnet":
            return command
        secret_registry = "0xE51d15dEbe0F037ae787336782e3dA43ba653a8D"
        token_network_registry = "0xdE8A2bdDF39C364e099D0637Dc1a7e2B8f73A4A5"
        service_registry = "0x4C3Abe4F53247F03A663b55FF02fD403BaBf176d"
        user_deposit = "0x19f8B656fBf17a83a5023eEbd675B1Ae5Bb5dF50"
        monitoring_service = "0x3B26A3d3D0c262359d1807863aE0D0FB6831D081"
        one_to_n = "0x7337e831cF5BD75B0045050E6C6549cf914A923D"
        #raiden --datadir $datadir --keystore-path $keystore  --network-id 4321 --accept-disclaimer --address $address --rpc --api-address 0.0.0.0:5001 --environment-type $env  --password-file $passwd_file --no-sync-check --accept-disclaimer --tokennetwork-registry-contract-address $TokenNetworkRegistry --secret-registry-contract-address $SecretRegistry  --gas-price 10000000000 --eth-rpc-endpoint 35.231.222.142:8546  --matrix-server https://raidentransport.exchangeunion.com --resolver-endpoint http://localhost:8887/resolveraiden --service-registry-contract-address $ServiceRegistry --one-to-n-contract-address $OneToN --user-deposit-contract-address $UserDeposit --monitoring-service-contract-address $MonitoringService --routing-mode private
        command = [
            "--environment-type development",
            "--routing-mode private",
            "--network-id 4321",
            "--no-sync-check",
            "--gas-price 10000000000",
            "--eth-rpc-endpoint 35.231.222.142:8546",
            "--tokennetwork-registry-contract-address {}".format(token_network_registry),
            "--secret-registry-contract-address {}".format(secret_registry),
            "--matrix-server https://raidentransport.exchangeunion.com",
            "--resolver-endpoint http://xud:8887/resolveraiden",
            "--service-registry-contract-address {}".format(service_registry),
            "--one-to-n-contract-address {}".format(one_to_n),
            "--user-deposit-contract-address {}".format(user_deposit),
            "--monitoring-service-contract-address {}".format(monitoring_service),
        ]
        return command

    def get_environment(self):
        environment = []
        if self.network == "simnet":
            return environment

        geth = self.config.nodes["geth"]
        if geth["mode"] == "external":
            rpc_host = geth["external_rpc_host"]
            rpc_port = geth["external_rpc_port"]
            environment.extend([
                f'RPC_ENDPOINT=http://{rpc_host}:{rpc_port}'
            ])
        elif geth["mode"] == "infura":
            project_id = geth["infura_project_id"]
            project_secret = geth["infura_project_secret"]
            if self.network == "mainnet":
                environment.extend([
                    f'RPC_ENDPOINT=https://mainnet.infura.io/v3/{project_id}'
                ])
            elif self.network == "testnet":
                environment.extend([
                    f'RPC_ENDPOINT=https://ropsten.infura.io/v3/{project_id}'
                ])
        return environment

    def status(self):
        status = super().status()
        if status == "exited":
            # TODO analyze exit reason
            return "Container exited"
        elif status == "running":
            try:
                tokens = self.api.get_tokens()
                if tokens:
                    return "Ready"
                else:
                    return "Waiting for sync"
            except RaidenApiError as e:
                if str(e) == "7|''":
                    output = "\n".join(list(self.logs(tail=1)))
                    if output == "Waiting for geth to be ready":
                        return "Waiting for sync"
                    elif "Waiting for the ethereum node to synchronize" in output:
                        # Raiden is running in production mode
                        # Checking if the ethereum node is synchronized
                        # Waiting for the ethereum node to synchronize. [Use ^C to exit]
                        return "Waiting for sync"
                    else:
                        return "Container running"
                self._logger.exception("Failed to get advanced running status")
                return str(e)
            except:
                self._logger.exception("Failed to get advanced running status")
                return "Container running"
        else:
            return status
