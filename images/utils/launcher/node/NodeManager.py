from __future__ import annotations

import os
import sys
import threading
import time
import logging
from typing import TYPE_CHECKING, Dict
import importlib
from dataclasses import dataclass

from .UpdateManager import UpdateManager
from .docker import DockerClientFactory, DockerTemplate
from launcher.utils import parallel_execute, execute, get_useful_error_message
if TYPE_CHECKING:
    from launcher.config import Config
    from launcher.shell import Shell
    from .Node import Node


__all__ = ["NodeManager", "Context"]

logger = logging.getLogger(__name__)


class NodeNotFound(Exception):
    pass


@dataclass
class Context:
    config: Config
    shell: Shell
    docker_client_factory: DockerClientFactory
    docker_template: DockerTemplate
    node_manager: NodeManager


class NodeManager:
    def __init__(self, config: Config, shell: Shell):
        self.config = config
        self.shell = shell
        self.docker_client_factory = DockerClientFactory()
        self.context = Context(
            config=self.config,
            shell=self.shell,
            docker_client_factory=self.docker_client_factory,
            docker_template=DockerTemplate(self.docker_client_factory),
            node_manager=self,
        )
        self.nodes = self._create_nodes()

        self.snapshots_dir = os.path.join(self.config.logs_dir, "snapshots")
        if not os.path.exists(self.snapshots_dir):
            os.makedirs(self.snapshots_dir)
        self.snapshot_file = os.path.join(self.snapshots_dir, f"snapshot-{self.config.launch_id}.yml")

        self.update_manager = UpdateManager(self.context)

    def _create_nodes(self) -> Dict[str, Node]:
        result = {}
        for service_name in self.config.nodes:
            module_name = service_name.capitalize()
            m = importlib.import_module("launcher.node." + module_name)
            instance = getattr(m, module_name)(service_name, self.context)
            result[service_name] = instance
        return result

    def save_snapshot(self, content: str):
        with open(self.snapshot_file, "w") as f:
            f.write(content)

    @property
    def network(self) -> str:
        return self.config.network

    @property
    def branch(self) -> str:
        return self.config.branch

    @property
    def client(self):
        return self.docker_client_factory.shared_client

    def get_node(self, name) -> Node:
        try:
            return self.valid_nodes[name]
        except KeyError:
            raise NodeNotFound(name)

    @property
    def valid_nodes(self):
        return {name: node for name, node in self.nodes.items() if node.mode == "native" and not node.disabled}

    @property
    def enabled_nodes(self):
        return {name: node for name, node in self.nodes.items() if not node.disabled}

    def update(self) -> None:
        self.update_manager.update()

    def up(self):
        nodes = self.valid_nodes.values()
        service_list = [n.name for n in nodes]
        cmd = f"docker-compose -f {self.snapshot_file} -p {self.network} up -d {' '.join(service_list)}"
        execute(cmd)

    def ensure(self):
        self.up()

    def down(self):
        cmd = f"docker-compose -f {self.snapshot_file} -p {self.network} down"
        execute(cmd)

    def create(self, *args):
        cmd = f"docker-compose -f {self.snapshot_file} -p {self.network} create {' '.join(args)}"
        execute(cmd)

    def logs(self, *args):
        cmd = f"docker-compose -f {self.snapshot_file} -p {self.network} logs {' '.join(args)}"
        execute(cmd)

    def start(self, *args):
        cmd = f"docker-compose -f {self.snapshot_file} -p {self.network} start {' '.join(args)}"
        execute(cmd)

    def stop(self, *args):
        cmd = f"docker-compose -f {self.snapshot_file} -p {self.network} stop {' '.join(args)}"
        execute(cmd)

    def restart(self, *args):
        cmd = f"docker-compose -f {self.snapshot_file} -p {self.network} restart {' '.join(args)}"
        execute(cmd)

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
        return not os.path.exists(f"{self.config.network_dir}/data/xud/nodekey.dat")

    def export(self) -> str:
        lines = [
            "# DO NOT EDIT THIS FILE!!!",
            "# It's generated by xud-docker utils:latest (revision)",  # TODO fill in xud-docker revision
            "# %s" % " ".join(sys.argv),
            "version: '2'",
            "services:",
        ]
        for name, service in self.enabled_nodes.items():
            service: Node
            lines.append(f"  {name}:")

            spec = service.container_spec

            # image
            lines.append(f"    image: {spec.image}")

            # hostname
            lines.append(f"    hostname: {name}")

            # command
            if len(spec.command) > 0:
                lines.append(f"    command: >")
                for arg in spec.command:
                    lines.append(f"      {arg}")

            # environment
            if len(spec.environment) > 0:
                lines.append(f"    environment:")
                for kv in spec.environment:
                    lines.append(f"      - {kv}")

            # ports
            if len(spec.ports) > 0:
                lines.append(f"    ports:")
                for key, value in spec.ports.items():
                    if key.endswith("/tcp"):
                        container_port = key.replace("/tcp", "")
                    else:
                        container_port = key
                    if isinstance(value, tuple):
                        host_port = "%s:%s" % value
                    else:
                        host_port = "%s" % value
                    lines.append(f"      - {host_port}:{container_port}")

            # volumes
            if len(spec.volumes) > 0:
                lines.append(f"    volumes:")
                for key, value in spec.volumes.items():
                    host_dir = key
                    container_dir = value["bind"]
                    mode = value["mode"]
                    if mode == "rw":
                        lines.append(f"      - {host_dir}:{container_dir}")
                    else:
                        lines.append(f"      - {host_dir}:{container_dir}:{mode}")

        return "\n".join(lines) + "\n"
