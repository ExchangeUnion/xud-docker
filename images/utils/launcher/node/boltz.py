import json
from .base import Node, CliBackend, CliError

class BoltzApiError(Exception):
    pass

class BoltzApi:
    def __init__(self, backend):
        self._backend = backend

    def getinfo(self):
        try:
            info = self._backend["getinfo"]()
            return json.loads(info)
        except CliError as e:
            raise BoltzApiError(e.output)

class Boltz(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        # TODO: allow to disable Boltz via config (arby-like)
        environment = []

        self.container_spec.environment.extend(environment)

        self._cli = "boltzcli"
        self.api = BoltzApi(CliBackend(self.client, self.container_name, self._logger, self._cli))

    def status(self):
        status = super().status()

        if status == "exited":
            return "Container exited"
        elif status == "running":
            try:
                self.api.getinfo()
                return "Ready"
            except:
                return "Waiting for Boltz to come up..."
        else:
            return status

        status = "Boltz"
        return status
    
