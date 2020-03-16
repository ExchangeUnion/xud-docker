import docker
from docker.models.containers import Container
from docker.errors import NotFound
from typing import List
from subprocess import check_output


class Action:
    def __init__(self, network, shell):
        self.network = network
        self.shell = shell
        self.client = docker.from_env()

    def execute(self):
        result: List[Container] = self.client.containers.list(all=True, filters={"name": f"{self.network}_utils"})
        hostname = check_output("hostname").decode().splitlines()[0]

        result = [c for c in result if c.attrs["Config"]["Hostname"] != hostname]

        n = len(result)

        if n == 0:
            return

        reply = self.shell.yes_or_no("Found {} existing xud ctl sessions. Do you want to close these?".format(n))
        if reply == "yes":
            for c in result:
                if c.status == "running":
                    print(f"Stopping {c.name}...")
                    c.stop()
            for c in result:
                print(f"Removing {c.name}...")
                try:
                    c.remove()
                except NotFound:
                    pass
