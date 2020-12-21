import argparse
import asyncio
import json
import logging
import os
import platform
import ssl
import sys
import time
from concurrent.futures import wait, ALL_COMPLETED
from datetime import datetime
from http.client import HTTPResponse
from threading import Event, Thread
from typing import List, Dict, cast, Optional
from urllib.error import HTTPError
from urllib.request import urlopen, Request
from queue import Queue

import aiohttp

from launcher.service import \
    Service, Context, \
    Proxy, Bitcoind, Litecoind, Geth, Lnd, Connext, Xud, Arby, Boltz, Webui
from launcher.utils import run
from launcher.errors import InvalidNetwork, InvalidService, UnsupportedFieldType, ServiceNotFound, SetupError, ExecutionError

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


class Launcher:
    services: Dict[str, Service]
    context: Context
    attach_thread: Thread
    loop: asyncio.AbstractEventLoop
    ws: Optional[aiohttp.ClientWebSocketResponse]

    def __init__(self, network: str, network_dir: str, *, loop: asyncio.AbstractEventLoop = None):
        if network not in presets:
            raise InvalidNetwork(network)

        self.context = Context(network, network_dir)

        self.services = self._init_services(presets[network])

        self.context.get_service = self.get_service

        if not loop:
            loop = asyncio.get_event_loop()

        self.loop = loop

        self.ws = None

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

    def apply(self, args):
        logger.debug("Applying configurations")
        # merge args and parsed into service.config
        for k, v in args.__dict__.items():
            if "." in k:
                parts = k.split(".")
                if len(parts) == 2:
                    s = self.get_service(parts[0])
                    setattr(s.config, parts[1], v)

        self._apply()

    def _apply(self):
        for name, service in self.services.items():
            service.apply()

    def get_service(self, name):
        try:
            return self.services[name]
        except KeyError:
            raise ServiceNotFound(name)

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

    def _stop_services(self, *names: str):
        run("docker-compose -p %s stop %s" % (self.network, " ".join(names)))

    async def _serve(self, queue: Queue):
        try:
            timeout = aiohttp.ClientTimeout(total=3)

            session = aiohttp.ClientSession(loop=self.loop, timeout=timeout)
            self.session = session

            url = cast(Proxy, self.get_service("proxy")).apiurl
            url = url + "/launcher"

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            async with session.ws_connect(url, ssl_context=ctx) as ws:
                queue.put(ws)

                logger.debug("[Attach] Successfully attached to proxy")
                logger.debug("[Attach] Waiting for messages from proxy")

                async for msg in ws:
                    logger.debug("[Attach] Got message: %r", msg)

                    msg: aiohttp.WSMessage
                    if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break

                    req = json.loads(msg.data)
                    method = req["method"]
                    params = req["params"]
                    if method == "getinfo":
                        resp = {"result": json.dumps(self.info), "error": None, "id": req["id"]}
                        logger.debug("[Attach] Sent response: %r", resp)
                        await ws.send_json(resp)
                    elif method == "backupto":
                        self.context.backup_dir = params[0]
                        self._apply()
                        self._export()
                        self.get_service("xud").up()

                logger.debug("[Attach] Stopped listening from proxy")

            logger.debug("[Attach] Disconnected from proxy")
        except Exception as e:
            queue.put(e)

    @property
    def info(self):
        return {
            "wallets": {
                "defaultPassword": self.context.default_password,
                "mnemonicShown": not self.context.default_password,
            },
            "backup": {
                "location": self.context.backup_dir,
                "defaultLocation": self.context.backup_dir == self.context.default_backup_dir,
            }
        }

    def attach(self) -> None:

        queue = Queue()

        def run(queue: Queue):
            logger.debug("[Attach] Begin")
            self.loop.run_until_complete(self._serve(queue))
            logger.debug("[Attach] End")

        self.attach_thread = Thread(target=run, args=(queue,), name="AttachThread")
        self.attach_thread.start()

        logger.debug("Waiting for WebSocket connection")
        ws = queue.get()
        if isinstance(ws, Exception):
            raise ws

        self.ws = ws
        logger.debug("Attached to proxy")

    def detach(self) -> None:
        if self.ws:
            logger.debug("Close WebSocket connection")
            asyncio.run_coroutine_threadsafe(self.ws.close(), loop=self.loop)
            logger.debug("Detached from proxy")

    def _setup_proxy_service(self) -> None:
        proxy = self.get_service("proxy")
        proxy.up()
        status = None
        while status != "Ready":
            status = proxy.status
            print("proxy: %s" % status)
            logger.debug("Service proxy status: %s", status)
            if status == "Container missing" or status == "Container exited":
                print("Failed to start proxy")
                raise SetupError("Failed to start proxy")
            time.sleep(3)

    def _setup_layer2_services(self) -> None:
        lndbtc = self.get_service("lndbtc")
        lndltc = self.get_service("lndltc")
        connext = self.get_service("connext")

        executor = self.context.executor

        executor.submit(lndbtc.up)
        executor.submit(lndltc.up)
        executor.submit(connext.up)

        def wait_lnd(lnd: Service, stop: Event):
            while not stop.is_set():
                s = lnd.status
                print("%s: %s" % (lnd.name, s))
                logger.debug("Service %s status: %s", lnd.name, s)
                if s == "Ready":
                    break
                if s.startswith("Syncing 100.00%"):
                    break
                if s.startswith("Syncing 99.99%"):  # happens in 2nd run
                    break
                if s.startswith("Wallet locked"):  # happens in 2nd run
                    break
                stop.wait(3)

        def wait_connext(connext: Service, stop: Event):
            while not stop.is_set():
                s = connext.status
                print("%s: %s" % (connext.name, s))
                logger.debug("Service %s status: %s", "connext", s)
                if s == "Ready":
                    break
                stop.wait(3)

        stop = Event()

        futs = [
            self.context.executor.submit(wait_lnd, lndbtc, stop),
            self.context.executor.submit(wait_lnd, lndltc, stop),
            self.context.executor.submit(wait_connext, connext, stop),
        ]

        try:
            done, not_done = wait(futs, return_when=ALL_COMPLETED)
        except KeyboardInterrupt:
            stop.set()
            raise

        for fut in done:
            fut.result()

        assert len(done) == 3

    def _setup_xud_service(self) -> None:
        xud = self.get_service("xud")
        xud.up()

        try:
            while True:
                status = xud.status
                print("xud: %s" % xud.status)
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
        except CreateError as e:
            raise SetupError("failed to create wallets: %s" % e) from e
        except UnlockError as e:
            raise SetupError("failed to unlock wallets: %s" % e) from e

    def _setup_additional_services(self) -> None:
        boltz = self.get_service("boltz")
        boltz.up()

    def setup(self) -> None:
        logger.debug("Setup %s (%s)", self.network, self.network_dir)
        cwd = os.getcwd()

        try:
            os.chdir(self.network_dir)

            self._export()

            self._setup_proxy_service()

            # attach to proxy
            self.attach()

            self._setup_layer2_services()

            self._setup_xud_service()

            self._setup_additional_services()

            print("Attached to proxy. Press Ctrl-C to detach from it.")
            self.attach_thread.join()
        finally:
            logger.debug("Shutdown thread pool executor")
            self.context.executor.shutdown(wait=False, cancel_futures=True)

            logger.debug("Detach from proxy")
            self.detach()

            while self.loop.is_running():
                logger.debug("The event loop is still running in AttachThread")
                self.loop.stop()
                time.sleep(1)

            os.chdir(cwd)

    def _create_wallets(self, password):
        url = cast(Proxy, self.get_service("proxy")).apiurl
        payload = json.dumps({"password": password})
        req = Request(f"{url}/api/v1/xud/create", headers={
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
            body = e.read().decode()
            body = body.strip()
            try:
                j = json.loads(body)
                raise CreateError("HTTP %s %s" % (e.code, j["message"])) from e
            except json.JSONDecodeError:
                raise CreateError("HTTP %s %s" % (e.code, "(empty body)" if body == "" else body)) from e

    def _unlock_wallets(self, password):
        url = cast(Proxy, self.get_service("proxy")).apiurl
        payload = json.dumps({"password": password})
        req = Request(f"{url}/api/v1/xud/unlock", headers={
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
            body = e.read().decode()
            body = body.strip()
            try:
                j = json.loads(body)
                raise UnlockError("HTTP %s %s" % (e.code, j["message"])) from e
            except json.JSONDecodeError:
                raise UnlockError("HTTP %s %s" % (e.code, "(empty body)" if body == "" else body)) from e

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

                field = field.replace("_", "-")

                if field_type == str:
                    g.add_argument(f"--{name}.{field}", type=str, default=value, help=help)
                elif field_type == bool:
                    g.add_argument(f"--{name}.{field}", type=str_to_bool, default=value, help=help)
                elif field_type == List[str]:
                    g.add_argument(f"--{name}.{field}", type=list, default=value, help=help)
                elif field_type == int:
                    g.add_argument(f"--{name}.{field}", type=int, default=value, help=help)
                else:
                    raise UnsupportedFieldType(field_type)


def str_to_bool(s):
    s = s.lower()
    if s not in ("true", "false", "1", "0", "yes", "no", "y", "n", "t", "f"):
        raise ValueError("not a valid boolean value: " + s)
    return s in ("true", "1", "yes", "y", "t")
