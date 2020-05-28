from docker.models.containers import Container as ContainerObject
from docker.errors import NotFound
from concurrent.futures import ThreadPoolExecutor, wait
import os

from .docker import DockerClientFactory, DockerRegistryClient, DockerTemplate
from .service import Service
from .types import XudNetwork
from .container import Container
from .image import Image


class RuntimeContext:
    def get_all_images(self) -> [Image]:
        pass

    def get_all_containers(self) -> [Container]:
        pass


class Context:
    def __init__(self, branch: str, network: XudNetwork, project_dir: str):
        self.network = network
        self.branch = branch
        self.project_dir = project_dir

        docker_client_factory = DockerClientFactory()
        docker_registry_client = DockerRegistryClient("https://registry-1.docker.io/v2", "https://auth.docker.io/token")

        self.docker_client_factory = docker_client_factory
        self.docker_registry_client = docker_registry_client
        self.docker_template = DockerTemplate(docker_client_factory, docker_registry_client)

        self._services = {
            "utils": Service(self.branch, self.docker_template, "utils", "exchangeunion/utils:latest", f"{self.network}_utils_1")
        }

    def get_service(self, name: str) -> Service:
        return self._services[name]

    @property
    def runtime(self) -> RuntimeContext:
        return RuntimeContext()

    def cleanup(self):
        client = self.docker_client_factory.shared_client

        docker_containers = []
        name_prefix = f"{self.network}_"
        containers: [Container] = client.containers.list(all=True, filters={"name": name_prefix})
        for c in containers:
            docker_containers.append(c.id)

        def remove(cid):
            c: ContainerObject = client.containers.get(cid)
            # print(cid)
            # print(c.attrs["State"]["Status"])
            # print(c.attrs["Name"][1:])
            name = c.attrs["Name"][1:]
            print(f"Remove {name}")
            c.stop()
            try:
                c.remove()
            except:
                pass

            try:
                client.containers.get(cid)
            except NotFound:
                pass

        n = len(docker_containers)

        if n <= 0:
            return

        with ThreadPoolExecutor(max_workers=n) as executor:
            fs = [executor.submit(remove, cid) for cid in docker_containers]
            done, not_done = wait(fs)
            print(done)
            print(not_done)

        network_dir = os.path.expanduser(f"~/.xud-docker/{self.network}")
        data_dir = f"{network_dir}/data"
        print(f"Remove {data_dir}")
        os.system(f"sudo rm -rf {data_dir}")
        network_conf = f"{network_dir}/simnet.conf"
        print(f"Remove {network_conf}")
        os.system(f"rm -f {network_conf}")

    def destroy(self):
        self.docker_client_factory.destroy()
