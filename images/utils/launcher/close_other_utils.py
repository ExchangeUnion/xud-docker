import docker
from docker.models.containers import Container
from docker.errors import APIError
from typing import List
from subprocess import check_output
import re


class Action:
    def __init__(self, network, shell):
        self.network = network
        self.shell = shell
        self.client = docker.from_env()

    def get_utils_containers(self):
        """This method replace old name matching with more exact cmd matching
        self.client.containers.list(all=True, filters={"name": f"{self.network}_utils"})
        :return:
        """
        containers = self.client.containers.list(all=True)
        result = []
        # Exclude self from the result
        hostname = check_output("hostname").decode().splitlines()[0]
        for c in containers:
            entrypoint = c.attrs["Config"]["Entrypoint"]
            cmd = c.attrs["Config"]["Cmd"]
            env = c.attrs["Config"]["Env"]
            if not entrypoint:
                continue
            if not cmd:
                continue
            if len(entrypoint) != 1 or entrypoint[0] != "python":
                continue
            if len(cmd) < 2:
                continue
            if cmd[0] != "-m" or cmd[1] != "launcher":
                continue
            if env and "NETWORK={}".format(self.network) in env and c.attrs["Config"]["Hostname"] != hostname:
                result.append(c)
        return result

    def execute(self):
        result: List[Container] = self.get_utils_containers()

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
                except APIError as e:
                    if e.status_code == 409:
                        # docker.errors.APIError: 409 Client Error: Conflict ("removal of container xxx is already in progress")
                        pass
                    else:
                        raise e
