from __future__ import annotations

import functools
import logging
import sys
import threading
from abc import ABC, abstractmethod
from concurrent.futures import wait
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict

import docker
from docker.errors import NotFound
from docker.types import IPAMConfig, IPAMPool

from launcher.utils import ArgumentParser, yes_or_no, parallel
from launcher.errors import FatalError
from .DockerTemplate import DockerTemplate
from .arby import Arby
from .base import Node, ContainerNotFound
from .bitcoind import Bitcoind, Litecoind
from .boltz import Boltz
from .connext import Connext
from .geth import Geth
from .image import Image, ImageManager
from .lnd import Lnd, Lndbtc, Lndltc
from .proxy import Proxy
from .webui import Webui
from .xud import Xud, XudApiError

if TYPE_CHECKING:
    from launcher.config import Config
    from docker.client import DockerClient

logger = logging.getLogger(__name__)


class Command(ABC):
    def __init__(self, get_service):
        self.get_service = get_service
        self.parser = self.create_parser()

    @abstractmethod
    def create_parser(self) -> ArgumentParser:
        pass

    @abstractmethod
    def execute(self, *args) -> None:
        pass


class LogsCommand(Command):
    def create_parser(self) -> ArgumentParser:
        parser = ArgumentParser(prog="logs", description="fetch the logs of a container")
        parser.add_argument("--tail", metavar='N',
                            help="number of lines to show from the end of the logs (default \"100\")",
                            default="100")
        parser.add_argument("--since",
                            help="show logs since timestamp (e.g. 2013-01-02T13:23:37) or relative (e.g. 42m for 42 minutes)")
        parser.add_argument("--until",
                            help="show logs before a timestamp (e.g. 2013-01-02T13:23:37) or relative (e.g. 42m for 42 minutes)")
        parser.add_argument("--follow", "-f", action="store_true",
                            help="follow log output")
        parser.add_argument("--timestamps", "-t", action="store_true",
                            help="show timestamps")
        parser.add_argument("service")
        return parser

    def execute(self, *args) -> None:
        args = self.parser.parse_args(args)
        name = args.service
        service = self.get_service(name)
        for line in service.logs(tail=args.tail, since=args.since, until=args.until, follow=args.follow,
                                 timestamps=args.timestamps):
            print(line)


class StartCommand(Command):
    def create_parser(self) -> ArgumentParser:
        parser = ArgumentParser(prog="start")
        parser.add_argument("service")
        return parser

    def execute(self, *args) -> None:
        args = self.parser.parse_args(args)
        name = args.service
        service = self.get_service(name)
        service.start()


class StopCommand(Command):
    def create_parser(self) -> ArgumentParser:
        parser = ArgumentParser(prog="stop")
        parser.add_argument("service")
        return parser

    def execute(self, *args) -> None:
        args = self.parser.parse_args(args)
        name = args.service
        service = self.get_service(name)
        service.stop()


class RestartCommand(Command):
    def create_parser(self) -> ArgumentParser:
        parser = ArgumentParser(prog="restart")
        parser.add_argument("service")
        return parser

    def execute(self, *args) -> None:
        args = self.parser.parse_args(args)
        name = args.service
        service = self.get_service(name)
        service.stop()
        service.start()


class RemoveCommand(Command):
    def create_parser(self) -> ArgumentParser:
        parser = ArgumentParser(prog="rm")
        parser.add_argument("service")
        return parser

    def execute(self, *args) -> None:
        args = self.parser.parse_args(args)
        name = args.service
        service = self.get_service(name)
        service.remove()


class CreateCommand(Command):
    def create_parser(self) -> ArgumentParser:
        parser = ArgumentParser(prog="create")
        parser.add_argument("service")
        return parser

    def execute(self, *args) -> None:
        args = self.parser.parse_args(args)
        name = args.service
        service = self.get_service(name)
        service.create()


@dataclass
class Context:
    config: Config
    client: docker.DockerClient
    image_manager: ImageManager
    node_manager: NodeManager


class ServiceNotFound(Exception):
    pass


class NetworkNotFound(Exception):
    pass


class NodeManager:
    config: Config
    client: DockerClient

    def __init__(self, config: Config):
        self.logger = logger

        self.config = config
        self.client = docker.from_env()
        self.image_manager = ImageManager(self.config, self.client)

        ctx = Context(self.config, self.client, self.image_manager, self)

        self.nodes = {name: globals()[name.capitalize()](name, ctx) for name in self.config.nodes}
        # self.docker_network = self.create_docker_network()

        self.cmd_logs = LogsCommand(self.get_service)
        self.cmd_start = StartCommand(self.get_service)
        self.cmd_stop = StopCommand(self.get_service)
        self.cmd_restart = RestartCommand(self.get_service)
        self.cmd_create = CreateCommand(self.get_service)
        self.cmd_remove = RemoveCommand(self.get_service)

        self.docker_template = DockerTemplate()

    @property
    def branch(self):
        return self.config.branch

    @property
    def network(self):
        return self.config.network

    @property
    def network_name(self):
        return self.network + "_default"

    def get_network_ipam_pool(self):
        # TODO smart IPAMPool creation
        if self.network == "simnet":
            return IPAMPool(subnet='10.0.1.0/24', gateway='10.0.1.1')
        elif self.network == "testnet":
            return IPAMPool(subnet='10.0.2.0/24', gateway='10.0.2.1')
        elif self.network == "mainnet":
            return IPAMPool(subnet='10.0.3.0/24', gateway='10.0.3.1')

    def _create_docker_network(self) -> None:
        ipam_pool = self.get_network_ipam_pool()
        ipam_config = IPAMConfig(pool_configs=[ipam_pool])
        network = self.client.networks.create(self.network_name, driver="bridge", ipam=ipam_config)
        logger.info("Created network: %r", network)

    def _remove_docker_network(self) -> None:
        network = self.docker_network
        network.remove()
        logger.info("Removed network: %r", network)

    @property
    def docker_network(self):
        try:
            return self.client.networks.get(self.network_name)
        except docker.errors.NotFound as e:
            raise NetworkNotFound(self.network_name) from e

    def get_service(self, name: str) -> Node:
        try:
            return self.nodes[name]
        except KeyError as e:
            raise ServiceNotFound(name) from e

    @property
    def valid_nodes(self) -> Dict[str, Node]:
        return {name: node for name, node in self.nodes.items() if node.mode == "native" and not node.disabled}

    def up(self):
        nodes = self.valid_nodes

        logger.info("Up services: %s", ", ".join(nodes))

        try:
            _ = self.docker_network
        except NetworkNotFound:
            self._create_docker_network()

        def linehead(node):
            return "starting %s" % node.container_name

        def start(node, stop):
            node.start()

        nodes = [node for node in nodes.values() if not node.is_running]

        parallel(self.config.executor, nodes, linehead, start)

    def down(self):
        nodes = self.valid_nodes

        logger.info("Down services: %s", ", ".join(nodes))

        running_nodes = [node for node in nodes.values() if node.is_running]

        parallel(self.config.executor, running_nodes,
                 lambda node: "stopping %s" % node.container_name,
                 lambda node, stop: node.stop())

        parallel(self.config.executor, list(nodes.values()),
                 lambda node: "removing %s" % node.container_name,
                 lambda node, stop: node.remove())

        print(f"Removing network {self.network_name}")
        self._remove_docker_network()

    def check_for_updates(self) -> Dict[Node, str]:
        logger.info("Checking for container updates")
        containers = self.nodes.values()
        result = {c: None for c in containers}

        executor = self.config.executor
        futs = {executor.submit(c.get_update_action): c for c in containers}
        done, not_done = wait(futs, 30)
        if len(not_done) > 0:
            raise RuntimeError("Failed to create all containers")
        for f in done:
            action = f.result()
            result[futs[f]] = action
        return result

    def _apply_changes(self, images, containers) -> None:

        pulls = [img for img, action in images.items() if action == "PULL"]

        if len(pulls) > 0:
            reply = yes_or_no(
                "A new version is available. Would you like to upgrade (Warning: this may restart your environment and cancel all open orders)?")
            if reply == "yes":
                for img in pulls:
                    img.pull()

        b1 = len(pulls) == 0
        b2 = functools.reduce(lambda r, item: r and item == "NONE", containers.values(), True)

        if b1 and b2:
            print("All up-to-date.")

        def linehead(node):
            action = containers[node]
            if action == "CREATE":
                return "creating %s" % node.container_name
            elif action == "RECREATE":
                return "recreating %s" % node.container_name
            elif action == "REMOVE":
                return "removing %s" % node.container_name

        def update(node, stop):
            action = containers[node]
            if action == "CREATE":
                node.create()
            elif action == "RECREATE":
                if node.is_running:
                    node.stop()
                node.remove()
                node.create()
            elif action == "REMOVE":
                if node.is_running:
                    node.stop()
                node.remove()

        items = []
        for container, action in containers.items():
            if action != "NONE":
                items.append(container)

        parallel(self.config.executor, items, linehead, update)

    def update(self) -> None:
        if self.config.disable_update:
            self.logger.info("Skip update checking")
            return

        print("🌍 Checking for updates...")

        images = self.image_manager.check_for_updates()
        containers = self.check_for_updates()

        for image, action in images.items():
            if action != "NONE":
                print("- Image %s: %s" % (image.name, action.lower()))

        for container, action in containers.items():
            if action != "NONE":
                print("- Container %s: %s" % (container.container_name, action.lower()))

        self._apply_changes(images, containers)

    def _get_status_nodes(self):
        optional_nodes = ["arby", "boltz", "webui", "proxy"]
        result = {}
        for node in self.nodes.values():
            if node.name in optional_nodes:
                c = self.docker_template.get_container(node.container_name)
                if c:
                    result[node.name] = node
            else:
                result[node.name] = node
        return result

    def status(self):
        # TODO migrate to ServiceTable
        nodes = self._get_status_nodes()
        names = list(nodes)

        BRIGHT_BLACK = "\033[90m"
        BLUE = "\033[34m"
        RESET = "\033[0m"
        BOLD = "\033[0;1m"

        col1_title = "SERVICE"
        col2_title = "STATUS"
        col1_width = max(max([len(name) for name in names]), len(col1_title))
        col2_width = 62 - col1_width - 7
        col1_fmt = "%%-%ds" % col1_width
        col2_fmt = "%%-%ds" % col2_width

        border_style = BRIGHT_BLACK
        service_style = BLUE
        title_style = BOLD

        print(f"{border_style}┌─%s─┬─%s─┐{RESET}" % ("─" * col1_width, "─" * col2_width))
        print(
            f"{border_style}│{RESET} {title_style}%s{RESET} {border_style}│{RESET} {title_style}%s{RESET} {border_style}│{RESET}" % (
                col1_fmt % col1_title, col2_fmt % col2_title))
        for name in names:
            print(f"{border_style}├─%s─┼─%s─┤{RESET}" % ("─" * col1_width, "─" * col2_width))
            print(
                f"{border_style}│{RESET} {service_style}%s{RESET} {border_style}│{RESET} {border_style}%s{RESET} {border_style}│{RESET}" % (
                    col1_fmt % name, col2_fmt % ""))
        print(f"{border_style}└─%s─┴─%s─┘{RESET}" % ("─" * col1_width, "─" * col2_width))

        lock = threading.Lock()

        def update_line(name, text, fetching=False):
            nonlocal border_style
            i = names.index(name)
            n = len(names)
            y = (n - i) * 2
            x = col1_width + 2
            if fetching:
                print(f"\033[%dA\033[%dC{border_style}%s{RESET}\033[%dD\033[%dB" % (
                    y, x + 3, col2_fmt % text[:col2_width], x + col2_width + 3, y), end="")
            else:
                print("\033[%dA\033[%dC%s\033[%dD\033[%dB" % (
                    y, x + 3, col2_fmt % text[:col2_width], x + col2_width + 3, y), end="")
            sys.stdout.flush()

        result = {name: None for name in names}

        def update_status(node: Node, status: str) -> None:
            assert status is not None
            nonlocal result
            with lock:
                result[node.name] = status
                update_line(node.name, status)

        class State:
            def __init__(self, result):
                self.counter = 0
                self.result = result

            def __repr__(self):
                return f"<State counter={self.counter} result={self.result}>"

        def fetching(state: State):
            with lock:
                for name, status in state.result.items():
                    if status is None:
                        dots = abs(3 - state.counter % 6)
                        update_line(name, "fetching" + "." * dots, fetching=True)

        def fetching_loop(stop_event: threading.Event):
            nonlocal result
            state = State(result)
            while not stop_event.is_set():
                fetching(state)
                state.counter += 1
                stop_event.wait(1)

        stop_fetching_animation = threading.Event()
        threading.Thread(target=fetching_loop, args=(stop_fetching_animation,), name="status_fetching").start()

        try:
            executor = self.config.executor

            def wrapper(node):
                try:
                    status = node.status()
                    update_status(node, status)
                except Exception as e:
                    logger.exception("Failed to get %s status", node.name)
                    update_status(node, str(e))

            futs = {executor.submit(wrapper, node): node for node in nodes.values()}
            done, not_done = wait(futs, 30)
            for f in not_done:
                node = futs[f]
                update_status(node, "timeout")
        finally:
            stop_fetching_animation.set()

    @property
    def newly_installed(self):
        xud = self.get_service("xud")
        return not xud.has_wallets()
