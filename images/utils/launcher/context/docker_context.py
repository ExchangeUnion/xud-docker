import threading
import docker
from docker.errors import NotFound
from docker.types import IPAMPool, IPAMConfig
from importlib import import_module
import logging

from docker.errors import NotFound, ImageNotFound
from concurrent.futures import ThreadPoolExecutor, as_completed, Future, wait
from typing import List, Dict
import time
import functools


class InvalidNetwork(Exception):
    pass


class ContainerNotFound(Exception):
    pass


class ImagesCheckAbortion(Exception):
    pass


class ContainersCheckAbortion(Exception):
    pass


class DockerNetwork:
    def __init__(self, client, config, name):
        self._client = client
        self.name = name
        network = config.network
        if network == "simnet":
            self.subnet = "10.0.1.0/24"
            self.gateway = "10.0.1.1"
        elif network == "testnet":
            self.subnet = "10.0.2.0/24"
            self.gateway = "10.0.2.1"
        elif network == "mainnet":
            self.subnet = "10.0.3.0/24"
            self.gateway = "10.0.3.1"
        else:
            raise InvalidNetwork(network)

    def create(self):
        try:
            network = self._client.networks.get(self.name)
            # TODO compare subnet, gateway and driver
            return network
        except NotFound:
            pass
        pool = IPAMPool(subnet=self.subnet, gateway=self.gateway)
        config = IPAMConfig(pool_configs=[pool])
        network = self._client.networks.create(self.name, driver="bridge", ipam=config)
        return network

    def destroy(self):
        try:
            network = self._client.networks.get(self.name)
            network.remove()
        except NotFound:
            pass


class UpdateChecker:
    def __init__(self, client, config, containers):
        self._logger = logging.getLogger("launcher.docker_context.UpdateChecker")
        self._client = client
        self._config = config
        self._containers = containers

    def check_image(self, name):
        client = docker.from_env()
        self._logger.debug("Checking image %s", name)
        missing = False
        local_image = None
        remote_name = None
        remote_image = None

        try:
            local = client.images.get(name)
            local_image = {
                "sha256": local.id.replace("sha256:", ""),
                "created": local.labels["com.exchangeunion.image.created"],
                "size": local.attrs["Size"]
            }
        except ImageNotFound:
            missing = True

        branch = self._config.branch
        branch_image_exists = True

        if branch != "master":
            try:
                remote_name = name + "__" + branch.replace("/", "-")
                remote = client.images.get_registry_data(remote_name).pull()
                remote_image = {
                    "sha256": remote.id.replace("sha256:", ""),
                    "created": remote.labels["com.exchangeunion.image.created"],
                    "size": remote.attrs["Size"]
                }
            except NotFound:
                branch_image_exists = False

        if branch == "master" or not branch_image_exists:
            try:
                remote_name = name
                registry_data = client.images.get_registry_data(remote_name)
                remote = registry_data.pull()
                remote_image = {
                    "sha256": remote.id.replace("sha256:", ""),
                    "created": remote.labels["com.exchangeunion.image.created"],
                    "size": remote.attrs["Size"]
                }
            except NotFound:
                if not missing:
                    return "local", None
                else:
                    raise Exception("Image not found")

        self._logger.debug("Comparing images\nlocal --- %r (%s)\ncloud --- %r (%s)", local_image, name, remote_image, remote_name)

        if missing:
            return "missing", remote_name

        if local_image["sha256"] == remote_image["sha256"]:
            return "up-to-date", remote_name
        else:
            if local_image["created"] > remote_image["created"]:
                return "newer", remote_name
            else:
                return "outdated", remote_name

    def _display_container_status_text(self, status):
        if status == "missing":
            return "missing"
        elif status == "outdated":
            return "outdated"
        elif status == "external_with_container":
            return "external"

    def yes_or_no(self, prompt):
        reply = input(prompt + " [Y/n] ")
        if reply == "y" or reply == "Y" or reply == "":
            return "yes"
        else:
            return "no"

    def check_updates(self):
        if self._config.disable_update:
            return

        outdated = False

        # Step 1. check all images
        print("🌍 Checking for updates...")
        images = set([c.image for c in self._containers.values()])
        images_check_result = {x: None for x in images}
        while len(images) > 0:
            max_workers = len(images)
            failed = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                fs = {executor.submit(self.check_image, x): x for x in images}
                done, not_done = wait(fs, 60)
                for f in done:
                    image = fs[f]
                    try:
                        result = f.result()
                        images_check_result[image] = result
                        self._logger.debug("Checked image %s: %r", image, result)
                    except Exception as e:
                        self._logger.exception("Failed to check image %s", image)
                        failed.append((image, "%s: %s" % (type(e).__name__, str(e))))
                for f in not_done:
                    image = fs[f]
                    failed.append((image, "timeout"))
            if len(failed) > 0:
                print("Failed to check for image updates.")
                for image, reason in failed:
                    print(f"* {image}: {reason}")
                answer = self.yes_or_no("Try again?")
                if answer == "yes":
                    images = [item[0] for item in failed]
                    continue
                else:
                    raise ImagesCheckAbortion()
            else:
                break

        # TODO handle image local status. Print a warning or give users a choice
        for image, result in images_check_result.items():
            status, pull_image = result
            if status in ["missing", "outdated"]:
                print("* Image %s: %s" % (image, status))
                outdated = True

        # Step 2. check all containers
        containers = self._containers.values()
        containers_check_result = {c: None for c in containers}
        while len(containers) > 0:
            max_workers = len(containers)
            failed = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                fs = {executor.submit(c.check_updates, images_check_result): c for c in containers}
                done, not_done = wait(fs, 60)
                for f in done:
                    container = fs[f]
                    try:
                        result = f.result()
                        containers_check_result[container] = result
                        self._logger.debug("Checked container %s: %r", container.container_name, result)
                    except Exception as e:
                        self._logger.exception("Failed to check container %s", container.container_name)
                        failed.append((container, "%s: %s" % (type(e).__name__, str(e))))
                for f in not_done:
                    container = fs[f]
                    failed.append((container, "timeout"))
            if len(failed) > 0:
                print("Failed to check for container updates.")
                for container, reason in failed:
                    print(f"* {container.container_name}: {reason}")
                answer = self.yes_or_no("Try again?")
                if answer == "yes":
                    containers = [item[0] for item in failed]
                    continue
                else:
                    raise ContainersCheckAbortion()
            else:
                break

        for container, result in containers_check_result.items():
            status, details = result
            # when internal -> external status will be "external_with_container"
            # when external -> internal status will be "missing" because we deleted the container before
            if status in ["missing", "outdated", "external_with_container"]:
                print("* Container %s: %s" % (container.container_name, self._display_container_status_text(status)))
                outdated = True

        if not outdated:
            print("All up-to-date.")
            return

        all_containers_missing = functools.reduce(lambda a, b: a and b[0] in ["missing", "external", "external_with_container"], containers_check_result.values(), True)

        if all_containers_missing:
            answer = "yes"
        else:
            answer = self.yes_or_no("A new version is available. Would you like to upgrade (Warning: this may restart your environment and cancel all open orders)?")

        if answer == "yes":
            # Step 1. update images
            for image, result in images_check_result.items():
                status, image_name = result
                if status in ["missing", "outdated"]:
                    print("Pulling %s" % image_name)
                    img = self._client.images.pull(image_name)
                    if "__" in image_name:
                        # image_name like exchangeunion/lnd:0.7.1-beta__feat-full-node
                        parts = image_name.split("__")
                        tag = parts[0]
                        print("Retagging %s to %s" % (image_name, tag))
                        img.tag(tag)

            # Step 2. update containers
            # 2.1) stop all running containers
            for container in self._containers.values():
                container.stop()
            # 2.2) recreate outdated containers
            for container, result in containers_check_result.items():
                container.update(result)


class DockerContext:
    def __init__(self, config):
        self._logger = logging.getLogger("launcher.DockerContext")
        self._client = docker.from_env()
        self._config = config

        network = config.network
        self._network = DockerNetwork(self._client, config, network + "_default")
        if network == "simnet":
            nodes = ["ltcd", "lndbtc", "lndltc", "raiden", "xud"]
            self._containers = self._create_containers(nodes, config)
        elif network == "testnet":
            nodes = ["bitcoind", "litecoind", "geth", "lndbtc", "lndltc", "raiden", "xud"]
            self._containers = self._create_containers(nodes, config)
        elif network == "mainnet":
            nodes = ["bitcoind", "litecoind", "geth", "lndbtc", "lndltc", "raiden", "xud"]
            self._containers = self._create_containers(nodes, config)
        else:
            raise InvalidNetwork(network)

        self._update_checker = UpdateChecker(self._client, self._config, self._containers)

    def _create_containers(self, nodes, config):
        result = {}
        for node in nodes:
            container = getattr(import_module(".node", "launcher"), node.capitalize())(self._client, config, node)
            result[node] = container
        return result

    def create(self):
        self._network.create()
        for name, container in self._containers.items():
            container.create()

    def start(self):
        for name, container in self._containers.items():
            container.start()

    def stop(self):
        for name, container in self._containers.items():
            container.stop()

    def destroy(self):
        for name, container in self._containers.items():
            container.destroy()
        self._network.destroy()

    def get_container(self, name):
        try:
            return self._containers[name]
        except KeyError:
            raise ContainerNotFound(name)

    def update(self):
        self._update_checker.check_updates()
        self.create()

    @property
    def network(self):
        return self._config.network

    @property
    def network_dir(self):
        return self._config.network_dir

    @property
    def config(self):
        return self._config

    def get_nodes(self):
        return self._containers

    def get_node(self, name):
        return self._containers.get(name, None)

    def get_containers(self):
        return self._containers
