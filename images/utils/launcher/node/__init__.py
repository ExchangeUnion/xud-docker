import functools
import logging
import os
import sys
import threading
import time
from dataclasses import dataclass

import docker
from docker.errors import NotFound
from docker.types import IPAMConfig, IPAMPool

from .arby import Arby
from .base import Node
from .boltz import Boltz
from .bitcoind import Bitcoind, Litecoind
from .btcd import Btcd, Ltcd
from .connext import Connext
from .geth import Geth
from .image import Image, ImageManager
from .lnd import Lndbtc, Lndltc
from .webui import Webui
from .xud import Xud, XudApiError
from ..config import Config
from ..errors import FatalError
from ..shell import Shell
from ..utils import parallel_execute, get_useful_error_message, get_hostfs_file, ArgumentParser


class LogsCommand:
    def __init__(self, get_container, shell):
        self._get_container = get_container
        self._shell = shell

        parser = ArgumentParser(prog="logs", description="fetch the logs of a container")
        parser.add_argument("--tail", metavar='N', type=int, help="number of lines to show from the end of the logs", default=100)
        parser.add_argument("container")
        self._parser = parser

    def execute(self, args):
        args = self._parser.parse_args(args)
        container = self._get_container(args.container)
        for line in container.logs(tail=args.tail):
            self._shell.println(line)


class StartCommand:
    def __init__(self, get_container, shell):
        self._get_container = get_container
        self._shell = shell

        parser = ArgumentParser(prog="start")
        parser.add_argument("container")
        self._parser = parser

    def execute(self, args):
        args = self._parser.parse_args(args)
        container = self._get_container(args.container)
        container.start()


class StopCommand:
    def __init__(self, get_container, shell):
        self._get_container = get_container
        self._shell = shell

        parser = ArgumentParser(prog="stop")
        parser.add_argument("container")
        self._parser = parser

    def execute(self, args):
        args = self._parser.parse_args(args)
        container = self._get_container(args.container)
        container.stop()


class RestartCommand:
    def __init__(self, get_container, shell):
        self._get_container = get_container
        self._shell = shell

        parser = ArgumentParser(prog="restart")
        parser.add_argument("container")
        self._parser = parser

    def execute(self, args):
        args = self._parser.parse_args(args)
        container = self._get_container(args.container)
        container.stop()
        container.start()


@dataclass
class Context:
    config: Config
    shell: Shell
    client: docker.DockerClient
    image_manager: ImageManager
    node_manager: 'NodeManager'


class NodeNotFound(Exception):
    pass


class NodeManager:
    def __init__(self, config, shell):
        self.logger = logging.getLogger("launcher.node.NodeManager")

        self.config = config
        self.shell = shell
        self.client = docker.from_env()
        self.image_manager = ImageManager(self.config, self.shell, self.client)

        self.branch = self.config.branch
        self.network = self.config.network

        ctx = Context(self.config, self.shell, self.client, self.image_manager, self)

        self.nodes = {name: globals()[name.capitalize()](name, ctx) for name in self.config.nodes}
        self.docker_network = self.create_docker_network()

        self.cmd_logs = LogsCommand(self.get_node, self.shell)
        self.cmd_start = StartCommand(self.get_node, self.shell)
        self.cmd_stop = StopCommand(self.get_node, self.shell)
        self.cmd_restart = RestartCommand(self.get_node, self.shell)

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

    def create_docker_network(self):
        name = self.network_name
        try:
            network = self.client.networks.get(name)
            return network
        except NotFound:
            pass
        ipam_pool = self.get_network_ipam_pool()
        ipam_config = IPAMConfig(pool_configs=[ipam_pool])
        network = self.client.networks.create(name, driver="bridge", ipam=ipam_config)
        return network

    def get_node(self, name):
        try:
            return self.valid_nodes[name]
        except KeyError:
            raise NodeNotFound(name)

    def check_wallets(self):
        pass

    def wait_for_channels(self):
        pass

    @property
    def valid_nodes(self):
        return {name: node for name, node in self.nodes.items() if node.mode == "native" and not node.disabled}

    @property
    def enabled_nodes(self):
        return {name: node for name, node in self.nodes.items() if not node.disabled}

    def up(self):
        self.docker_network = self.create_docker_network()

        nodes = self.valid_nodes.values()

        def print_failed(failed):
            print("Failed to start these nodes.")
            for f in failed:
                print(f"- {f[0].name}: {str(f[1])}")

        def try_again():
            answer = self.shell.yes_or_no("Try again?")
            return answer == "yes"

        parallel_execute(nodes, lambda n: n.start(), 60, print_failed, try_again)

        if self.network in ["testnet", "mainnet"]:
            self.check_wallets()
        elif self.network == "simnet":
            self.wait_for_channels()

    def down(self):
        nodes = self.valid_nodes

        for name, container in nodes.items():
            print(f"Stopping {name}...")
            container.stop()
        for name, container in nodes.items():
            print(f"Removing {name}...")
            container.remove()
        print(f"Removing network {self.network_name}")
        self.docker_network.remove()

    def _display_container_status_text(self, status):
        if status == "missing":
            return "missing"
        elif status == "outdated":
            return "outdated"
        elif status == "external_with_container":
            return "non-native"
        elif status == "disabled_with_container":
            return "disabled"

    def _readable_details(self, details):
        if not details:
            return None
        diff_keys = [key for key, value in details.items() if not value.same]
        return ", ".join(diff_keys)

    def update(self) -> bool:
        if self.config.disable_update:
            return True

        outdated = False

        # Step 1. check all images
        print("🌍 Checking for updates...")
        images = self.image_manager.check_for_updates()

        self.logger.debug("[Update] Image checking result: %r", images)

        # TODO handle image local status. Print a warning or give users a choice
        for image in images:
            status = image.status
            if status in ["LOCAL_MISSING", "LOCAL_OUTDATED"]:
                print("- Image %s: %s" % (image.name, image.status_message))
                outdated = True
            elif status == "UNAVAILABLE":
                all_unavailable_images = [x for x in images if x.status == "UNAVAILABLE"]
                raise FatalError("Image(s) not available: %r" % all_unavailable_images)

        # Step 2. check all containers
        containers = self.nodes.values()
        container_check_result = {c: None for c in containers}

        def print_failed(failed):
            print("Failed to check for container updates.")
            for container, error in failed:
                print("- {}: {}".format(container.name, get_useful_error_message(error)))

        def try_again():
            answer = self.shell.yes_or_no("Try again?")
            return answer == "yes"

        def handle_result(container, result):
            container_check_result[container] = result

        parallel_execute(containers, lambda c: c.check_for_updates(), 60, print_failed, try_again, handle_result)

        self.logger.debug("[Update] Container checking result: %r", container_check_result)

        for container, result in container_check_result.items():
            status, details = result
            # when mode internal -> external or others, status will be "external_with_container"
            # when mode external or others -> internal, status will be "missing" because we deleted the container before
            # when disabled False -> True, status will be "disabled_with_container"
            # when disabled True -> False, status will be "missing" because we deleted the container before
            if status in ["missing", "outdated", "external_with_container", "disabled_with_container"]:
                readable_details = self._readable_details(details)
                if readable_details:
                    print("- Container %s: %s (%s)" % (container.container_name, self._display_container_status_text(status), readable_details))
                else:
                    print("- Container %s: %s" % (container.container_name, self._display_container_status_text(status)))
                outdated = True

        if not outdated:
            print("All up-to-date.")
            return True

        all_containers_missing = functools.reduce(lambda a, b: a and b[0] in ["missing", "external", "disabled"], container_check_result.values(), True)

        if all_containers_missing:
            answer = "yes"
        else:
            answer = self.shell.yes_or_no("A new version is available. Would you like to upgrade (Warning: this may restart your environment and cancel all open orders)?")

        if answer == "yes":
            # Step 1. update images
            self.image_manager.update_images()

            # Step 2. update containers
            # 2.1) stop all running containers
            for container in containers:
                container.stop()
            # 2.2) recreate outdated containers
            for container, result in container_check_result.items():
                container.update(result)
        else:
            return False

    def logs(self, *args):
        self.cmd_logs.execute(args)

    def start(self, *args):
        self.cmd_start.execute(args)

    def stop(self, *args):
        self.cmd_stop.execute(args)

    def restart(self, *args):
        self.cmd_restart.execute(args)

    def cli(self, name, *args):
        self.get_node(name).cli(" ".join(args), self.shell)

    def status(self):
        # TODO migrate to ServiceTable
        nodes = self.enabled_nodes
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
            f"{border_style}│{RESET} {title_style}%s{RESET} {border_style}│{RESET} {title_style}%s{RESET} {border_style}│{RESET}" % (col1_fmt % col1_title, col2_fmt % col2_title))
        for name in names:
            print(f"{border_style}├─%s─┼─%s─┤{RESET}" % ("─" * col1_width, "─" * col2_width))
            print(f"{border_style}│{RESET} {service_style}%s{RESET} {border_style}│{RESET} {border_style}%s{RESET} {border_style}│{RESET}" % (col1_fmt % name, col2_fmt % ""))
        print(f"{border_style}└─%s─┴─%s─┘{RESET}" % ("─" * col1_width, "─" * col2_width))

        lock = threading.Lock()

        def update_line(name, text, fetching=False):
            nonlocal border_style
            i = names.index(name)
            n = len(names)
            y = (n - i) * 2
            x = col1_width + 2
            if fetching:
                print(f"\033[%dA\033[%dC{border_style}%s{RESET}\033[%dD\033[%dB" % (y, x + 3, col2_fmt % text[:col2_width], x + col2_width + 3, y), end="")
            else:
                print("\033[%dA\033[%dC%s\033[%dD\033[%dB" % (y, x + 3, col2_fmt % text[:col2_width], x + col2_width + 3, y), end="")
            sys.stdout.flush()

        result = {name: None for name in names}

        def update_status(node, status):
            nonlocal result
            with lock:
                result[node.name] = status
                update_line(node.name, status)

        def status_wrapper(container, name, update_status):
            status = container.status()
            if status.startswith("could not connect"):
                update_status(name, "Waiting for xud...")
                time.sleep(5)
                status = container.status()

            update_status(name, status)

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

        def print_failed(failed):
            for node, error in failed:
                update_status(node, get_useful_error_message(error))

        def try_again():
            return False

        def handle_result(node, result):
            update_status(node, result)

        parallel_execute(nodes.values(), lambda n: n.status(), 30, print_failed, try_again, handle_result)

        stop_fetching_animation.set()

    @property
    def newly_installed(self):
        return not os.path.exists(f"{get_hostfs_file(self.config.network_dir)}/data/xud/nodekey.dat")
