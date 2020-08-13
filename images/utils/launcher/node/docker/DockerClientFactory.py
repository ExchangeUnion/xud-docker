import docker


class DockerClientFactory:
    def __init__(self):
        self.shared_client = docker.from_env(timeout=604800)

