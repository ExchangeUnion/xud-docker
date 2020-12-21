import argparse
import json
import os
import platform
import re
import sys
import time
from datetime import datetime
from typing import List, Dict, cast
import logging
from concurrent.futures import wait, ALL_COMPLETED
from threading import Event
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from http.client import HTTPResponse
import ssl

from .arby import Arby
from .base import Service, Context
from .bitcoind import Bitcoind
from .boltz import Boltz
from .connext import Connext
from .errors import InvalidNetwork, InvalidService, UnsupportedFieldType, ServiceNotFound, SubprocessError
from .geth import Geth
from .litecoind import Litecoind
from .lnd import Lnd
from .proxy import Proxy
from .webui import Webui
from .xud import Xud
from .utils import run


logger = logging.getLogger(__name__)

presets = {
    "simnet": [
        "proxy", "lndbtc", "lndltc", "connext", "xud", "arby", "webui"
    ],
    "testnet": [
        "proxy", "bitcoind", "litecoind", "geth", "lndbtc", "lndltc", "connext", "xud", "arby", "boltz", "webui"
    ],
    "mainnet": [
        "proxy", "bitcoind", "litecoind", "geth", "lndbtc", "lndltc", "connext", "xud", "arby", "boltz", "webui"
    ],
}

DEFAULT_WALLET_PASSWORD = "OpenDEX!Rocks"


class CreateError(Exception):
    pass


class UnlockError(Exception):
    pass


class ServiceManager:
    services: Dict[str, Service]
    context: Context

    def __init__(self, network: str, network_dir: str):
        if network not in presets:
            raise InvalidNetwork(network)

        self.context = Context(network, network_dir)

        self.services = self._init_services(presets[network])

        self.context.get_service = self.get_service

    @property
    def network(self) -> str:
        return self.context.network

    @property
    def network_dir(self) -> str:
        return self.context.network_dir

    def _init_services(self, names: List[str]) -> Dict[str, Service]:
        result = {}
        for name in names:
            if name == "proxy":
                service = Proxy(self.context, name)
            elif name == "bitcoind":
                service = Bitcoind(self.context, name)
            elif name == "litecoind":
                service = Litecoind(self.context, name)
            elif name == "geth":
                service = Geth(self.context, name)
            elif name == "lndbtc":
                service = Lnd(self.context, name, "bitcoin")
            elif name == "lndltc":
                service = Lnd(self.context, name, "litecoin")
            elif name == "connext":
                service = Connext(self.context, name)
            elif name == "xud":
                service = Xud(self.context, name)
            elif name == "arby":
                service = Arby(self.context, name)
            elif name == "boltz":
                service = Boltz(self.context, name)
            elif name == "webui":
                service = Webui(self.context, name)
            else:
                raise InvalidService(name)
            result[name] = service

        return result

    def apply(self):
        logger.debug("Applying configurations")
        # merge args and parsed into service.config
        for name, service in self.services.items():
            service.apply()

    def get_service(self, name):
        try:
            return self.services[name]
        except KeyError:
            raise ServiceNotFound(name)

    def get_status(self, name):
        return self.get_service(name).status

    def _export(self) -> None:
        # docker-compose.yml
        try:
            with open("docker-compose.yml", "w") as f:
                f.write(self._export_docker_compose_yaml())
        except PermissionError:
            if platform.system() in ["Linux", "Darwin"]:
                print("Fix network folder (%s) permission" % self.network_dir)
                cmd = "sudo chown -R {user}:{user} .".format(user=os.getenv("USER"))
                exit_code = os.system(cmd)
                if exit_code != 0:
                    print("Failed to fix network folder (%s) permission" % self.network_dir)
                    sys.exit(1)
            else:
                raise

        # data/config.json
        if not os.path.exists("data"):
            os.mkdir("data")

        with open("data/config.json", "w") as f:
            f.write(self._export_config_json())

    def export(self) -> None:
        current_dir = os.getcwd()
        try:
            os.chdir(self.network_dir)
            self._export()
        finally:
            os.chdir(current_dir)

    def _export_docker_compose_yaml(self) -> str:
        result = "version: \"2.4\"\n"
        result += "services:\n"
        for name, service in self.services.items():
            if service.disabled:
                continue

            result += f"  {name}:\n"
            result += f"    image: {service.image}\n"
            if service.hostname:
                result += f"    hostname: {service.hostname}\n"

            if service.command:
                result += f"    command: >\n"
                for arg in service.command:
                    result += f"      {arg}\n"

            if service.environment:
                result += f"    environment:\n"
                for key, value in service.environment.items():
                    if "\n" in value:
                        result += f"      - >\n"
                        result += f"        {key}=\n"
                        for line in value.splitlines():
                            result += f"        {line}\n"
                    else:
                        result += f"      - {key}={value}\n"

            if service.volumes:
                result += f"    volumes:\n"
                for volume in service.volumes:
                    result += f"      - {volume}\n"

            if service.ports:
                result += f"    ports:\n"
                for port in service.ports:
                    result += f"      - {port}\n"

            if name == "xud":
                result += "    entrypoint: [\"bash\", \"-c\", \"echo /root/backup > /root/.xud/.backup-dir-value && /entrypoint.sh\"]\n"
        return result

    def _export_config_json(self) -> str:
        services = []
        config = {
            "timestamp": "%s" % int(datetime.now().timestamp()),
            "network": self.network,
            "services": services,
        }
        for name, service in self.services.items():
            if name == "proxy":
                continue
            services.append(service.to_json())
        return json.dumps(config, indent=2)

    def _remove_container(self, cid: str):
        try:
            run("docker stop %s" % cid)
            run("docker rm %s" % cid)
        except SubprocessError:
            logger.info("Failed to remove container %s. Will try to remove it forcefully.")
            run("docker rm -f %s")

    def _up_services(self, *names: str):
        while True:
            cmd = "docker-compose -p %s up -d %s" % (self.network, " ".join(names))
            try:
                run(cmd)
                break
            except SubprocessError as e:
                text = str(e)
                p = re.compile(r'^ERROR: for (.*)  .*The container name "/(.*)" is already in use by container "(.*)".*$')
                found = False
                for line in text.splitlines():
                    m = p.match(line)
                    if m:
                        found = True
                        sname = m.group(1)
                        if sname in names:
                            cname = m.group(2)
                            cid = m.group(3)
                            logger.info("Removing container %s (%s)", cname, cid)
                            self._remove_container(cid)
                if not found:
                    raise
            time.sleep(3)

    def _stop_services(self, *names: str):
        run("docker-compose -p %s stop %s" % (self.network, " ".join(names)))

    def setup(self) -> None:
        logger.debug("Setup %s (%s)", self.network, self.network_dir)
        current_dir = os.getcwd()
        try:
            os.chdir(self.network_dir)

            self._export()

            self._up_services("proxy")

            status = None

            while status != "Ready":
                status = self.get_status("proxy")
                logger.debug("Service proxy status: %s", status)

            self._up_services("lndbtc", "lndltc", "connext")

            def wait_lnd(name: str, stop: Event):
                while not stop.is_set():
                    s = self.get_status(name)
                    logger.debug("Service %s status: %s", name, s)
                    if s == "Ready":
                        break
                    if s.startswith("Syncing 100.00%"):
                        break
                    if s.startswith("Syncing 99.99%"):  # happens in 2nd run
                        break
                    stop.wait(3)

            def wait_connext(stop: Event):
                while not stop.is_set():
                    s = self.get_status("connext")
                    logger.debug("Service %s status: %s", "connext", s)
                    if s == "Ready":
                        break
                    stop.wait(3)

            stop = Event()

            futs = [
                self.context.executor.submit(wait_lnd, "lndbtc", stop),
                self.context.executor.submit(wait_lnd, "lndltc", stop),
                self.context.executor.submit(wait_connext, stop),
            ]

            try:
                done, not_done = wait(futs, return_when=ALL_COMPLETED)
            except KeyboardInterrupt:
                stop.set()
                raise

            for fut in done:
                fut.result()

            assert len(done) == 3

            self._up_services("xud")

            while True:
                status = self.get_status("xud")
                logger.debug("Service %s status: %s", "xud", status)
                if status.startswith("Wallet missing"):
                    self._create_wallets(DEFAULT_WALLET_PASSWORD)
                    break
                elif status.startswith("Wallet locked"):
                    self._unlock_wallets(DEFAULT_WALLET_PASSWORD)
                    break
                elif status == "Ready":
                    break
                elif status == "Waiting for channels":
                    break
                else:
                    time.sleep(3)

            self._up_services("boltz")
        finally:
            os.chdir(current_dir)

    def _create_wallets(self, password):
        port = cast(Proxy, self.get_service("proxy")).apiport
        payload = json.dumps({"password": password})
        req = Request(f"https://localhost:{port}/api/v1/xud/create", headers={
            "Content-Type": "application/json"
        }, data=payload.encode(), method="POST")

        # FIXME ignore tls
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            resp: HTTPResponse = urlopen(req, context=ctx)
            return json.load(resp)
        except HTTPError as e:
            raise CreateError(json.load(e)["message"])

    def _unlock_wallets(self, password):
        port = cast(Proxy, self.get_service("proxy")).apiport
        payload = json.dumps({"password": password})
        req = Request(f"https://localhost:{port}/api/v1/xud/unlock", headers={
            "Content-Type": "application/json"
        }, data=payload.encode(), method="POST")

        # FIXME ignore tls
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            resp: HTTPResponse = urlopen(req, context=ctx)
            return json.load(resp)
        except HTTPError as e:
            raise CreateError(json.load(e)["message"])

    def _down_services(self):
        run("docker-compose -p %s down" % self.network)

    def _remove_files(self):
        assert os.getcwd() == self.network_dir
        reply = input("Do you want to remove all contents in folder %s? [y/N] " % self.network_dir)
        reply = reply.strip()
        reply = reply.lower()
        if reply == "yes" or reply == "y":
            for f in os.listdir(self.network_dir):
                run("sudo rm -rf " + f)

    def cleanup(self) -> None:
        logger.debug("Cleanup %s (%s)", self.network, self.network_dir)
        current_dir = os.getcwd()
        try:
            os.chdir(self.network_dir)
            if os.path.exists("docker-compose.yml"):
                logger.debug("Stopping running services")
                self._stop_services("boltz")
                self._stop_services("xud")
                self._stop_services("lndbtc", "lndltc", "connext")
                self._stop_services("proxy")

                logger.debug("Removing containers and network")
                self._down_services()

            logger.debug("Removing files")
            self._remove_files()
        finally:
            os.chdir(current_dir)

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        for name, service in self.services.items():
            g = parser.add_argument_group(name)
            t = type(service.config)

            fields = {}

            for b in reversed(t.__mro__[:-1]):
                fields.update(b.__annotations__)

            fields_metadata = {}
            if hasattr(t, "__dataclass_fields__"):
                for field in fields:
                    if field in t.__dataclass_fields__:
                        fields_metadata[field] = t.__dataclass_fields__[field].metadata

            for field, field_type in fields.items():
                try:
                    value = getattr(service.config, field)
                except AttributeError:
                    value = None

                if field in fields_metadata:
                    help: str = fields_metadata[field]["help"] + " (default: %(default)r)"
                    help = help.replace("%(name)s", name)
                    help = help.capitalize()
                else:
                    help = "(default: %(default)s)"

                if field_type == str:
                    g.add_argument(f"--{name}.{field}", type=str, default=value, help=help)
                elif field_type == bool:
                    g.add_argument(f"--{name}.{field}", type=bool, default=value, help=help)
                elif field_type == List[str]:
                    g.add_argument(f"--{name}.{field}", type=list, default=value, help=help)
                elif field_type == int:
                    g.add_argument(f"--{name}.{field}", type=int, default=value, help=help)
                else:
                    raise UnsupportedFieldType(field_type)
