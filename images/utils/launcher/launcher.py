import os
import docker
from docker.types import IPAMPool, IPAMConfig
from docker.errors import NotFound, ImageNotFound
from concurrent.futures import ThreadPoolExecutor, as_completed, Future, wait
from .config import Config, ArgumentParser, ArgumentError
from .node import Node, Bitcoind, Litecoind, Ltcd, Geth, Lndbtc, Lndltc, Raiden, Xud, PasswordNotMatch, MnemonicNot24Words, InvalidPassword, LndApiError, XudApiError
import logging
from typing import List, Dict
import time
from .shell import Shell
import functools
import sys
import threading
import shlex
import toml

CONTAINERS = {
    "simnet": ["ltcd", "lndbtc", "lndltc", "raiden", "xud"],
    "testnet": ["bitcoind", "litecoind", "geth", "lndbtc", "lndltc", "raiden", "xud"],
    "mainnet": ["bitcoind", "litecoind", "geth", "lndbtc", "lndltc", "raiden", "xud"],
}

BRIGHT_BLACK = "\033[90m"
BLUE = "\033[34m"
RESET = "\033[0m"
BOLD = "\033[0;1m"


class ImagesCheckAbortion(Exception):
    def __init__(self, failed):
        super().__init__()
        self.failed = failed


class ContainersCheckAbortion(Exception):
    def __init__(self, failed):
        super().__init__()
        self.failed = failed


class ContainersEnsureAbortion(Exception):
    def __init__(self, failed):
        super().__init__()
        self.failed = failed


class BackupDirNotAvailable(Exception):
    pass


class RestoreDirNotAvailable(Exception):
    pass


class RestoreCancelled(Exception):
    pass


class NetworkConfigFileSyntaxError(Exception):
    def __init__(self, hint):
        super().__init__(hint)


class ImagesNotAvailable(Exception):
    def __init__(self, images):
        super().__init__()
        self.images = images


class ContainerNotFound(Exception):
    def __init__(self, container):
        super().__init__(container)
        self.container = container


class LogsCommand:
    def __init__(self, get_container, shell):
        self._get_container = get_container
        self._shell = shell

        parser = ArgumentParser(prog="logs", description="fetch the logs of a container")
        parser.add_argument("--tail", metavar='N', type=int, help="number of lines to show from the end of the logs")
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


class XudEnv:
    def __init__(self, config: Config, shell: Shell):
        self._client = docker.from_env()
        self._config = config
        self._shell = shell

        self._logger = logging.getLogger("launcher.XudEnv")

        self._docker_network = self.create_docker_network()

        self._containers: Dict[str, Node] = {}
        self.init_containers(self.network, self._client, config)

        self._cmd_logs = LogsCommand(self.get_container, self._shell)
        self._cmd_start = StartCommand(self.get_container, self._shell)
        self._cmd_stop = StopCommand(self.get_container, self._shell)
        self._cmd_restart = RestartCommand(self.get_container, self._shell)

    def init_containers(self, network, client, config):
        self._containers = {c: globals()[c.capitalize()](client, config, c) for c in CONTAINERS[network]}

    @property
    def network(self):
        return self._config.network

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

    def get_container(self, name):
        try:
            return self._containers[name]
        except KeyError:
            raise ContainerNotFound(name)

    def create_docker_network(self):
        name = self.network_name
        try:
            network = self._client.networks.get(name)
            return network
        except NotFound:
            pass
        ipam_pool = self.get_network_ipam_pool()
        ipam_config = IPAMConfig(pool_configs=[ipam_pool])
        network = self._client.networks.create(name, driver="bridge", ipam=ipam_config)
        return network

    def delegate_cmd_to_xucli(self, cmd):
        self._containers["xud"].cli(cmd, self._shell)

    def command_status(self):
        containers = self._containers
        names = list(containers)
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
        print(f"{border_style}│{RESET} {title_style}%s{RESET} {border_style}│{RESET} {title_style}%s{RESET} {border_style}│{RESET}" % (col1_fmt % col1_title, col2_fmt % col2_title))
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

        def update_status(name, status):
            nonlocal result
            with lock:
                result[name] = status
                update_line(name, status)

        def status_wrapper(container, name, update_status):
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
            self._logger.debug("fetching loop end")

        stop_fetching_animation = threading.Event()
        threading.Thread(target=fetching_loop, args=(stop_fetching_animation,), name="Animation").start()

        while len(containers) > 0:
            failed = {}
            with ThreadPoolExecutor(max_workers=len(containers)) as executor:
                fs = {executor.submit(status_wrapper, container, name, update_status): (name, container) for name, container in self._containers.items()}
                done, not_done = wait(fs, 30)
                for f in done:
                    name, container = fs[f]
                    try:
                        f.result()
                    except Exception as e:
                        self._logger.exception("Failed to get %s status", name)
                        failed[name] = str(e)
                for f in not_done:
                    name, container = fs[f]
                    self._logger.debug("Get %s status timeout", name)
                    failed[name] = "timeout"
            if len(failed) > 0:
                for container, error in failed.items():
                    update_status(container, error)
            containers = {}

        stop_fetching_animation.set()

    def command_down(self):
        for name, container in self._containers.items():
            print(f"Stopping {name}...")
            container.stop()
        for name, container in self._containers.items():
            print(f"Removing {name}...")
            container.remove()
        print(f"Removing network {self.network_name}")
        self._docker_network.remove()

    def command_up(self):
        print(f"Creating network: {self.network_name}")
        self._docker_network = self.create_docker_network()
        for c in self._containers.values():
            c: Node
            c.start()

    def command_report(self):
        network_dir = f"{self._config.home_dir}/{self.network}"
        print(f"""Please click on https://github.com/ExchangeUnion/xud/issues/\
new?assignees=kilrau&labels=bug&template=bug-report.md&title=Short%2C+concise+\
description+of+the+bug, describe your issue, drag and drop the file "xud-docker\
.log" which is located in "{network_dir}" into your browser window and submit \
your issue.""")

    def update_command(self, new_cmd):
        pass

    def _cmd_cli(self, name, args):
        self.get_container(name).cli(" ".join(args), self._shell)

    def handle_command(self, cmd):
        try:
            args = shlex.split(cmd)
            arg0 = args[0]
            args = args[1:]
            if arg0 == "status":
                self.command_status()
            elif arg0 == "report":
                self.command_report()
            elif arg0 == "start":
                self._cmd_start.execute(args)
            elif arg0 == "stop":
                self._cmd_stop.execute(args)
            elif arg0 == "restart":
                self._cmd_restart.execute(args)
            elif arg0 == "down":
                self.command_down()
            elif arg0 == "up":
                self.command_up()
            elif arg0 == "logs":
                self._cmd_logs.execute(args)
            elif arg0 == "btcctl":
                self._cmd_cli("btcd", args)
            elif arg0 == "ltcctl":
                self._cmd_cli("ltcd", args)
            elif arg0 == "bitcoin-cli":
                self._cmd_cli("bitcoind", args)
            elif arg0 == "litecoin-cli":
                self._cmd_cli("litecoind", args)
            elif arg0 == "lndbtc-lncli":
                self._cmd_cli("lndbtc", args)
            elif arg0 == "lndltc-lncli":
                self._cmd_cli("lndltc", args)
            elif arg0 == "geth":
                self._cmd_cli("geth", args)
            elif arg0 == "xucli":
                self._cmd_cli("xud", args)
            else:
                self.delegate_cmd_to_xucli(cmd)
        except ContainerNotFound as e:
            self._shell.println(f"Container not found: {e.container}")
        except ArgumentError as e:
            self._logger.exception("Command argument error: %s", cmd)
            self._shell.print(e.usage)
            self._shell.println(f"error: {e}")

    def check_image(self, name):
        self._logger.debug("Checking image: %s", name)
        missing = False
        local_image = None
        remote_name = None
        remote_image = None

        try:
            local = self._client.images.get(name)
            local_image = {
                "sha256": local.id.replace("sha256:", ""),
                "created": local.labels["com.exchangeunion.image.created"],
                "size": local.attrs["Size"]
            }
            # self._logger.debug("(%s) created at %s, size: %s", local_image["sha256"][:6], local_image["created"], local_image["size"])
        except ImageNotFound:
            missing = True

        branch = self._config.branch
        branch_image_exists = True

        if branch != "master":
            try:
                remote_name = name + "__" + branch.replace("/", "-")
                remote = self._client.images.get_registry_data(remote_name).pull()
                remote_image = {
                    "sha256": remote.id.replace("sha256:", ""),
                    "created": remote.labels["com.exchangeunion.image.created"],
                    "size": remote.attrs["Size"]
                }
                # self._logger.debug("%s: (%s) created at %s, size: %s", remote_name, remote_image["sha256"][:6], remote_image["created"], remote_image["size"])
            except NotFound:
                branch_image_exists = False
                self._logger.debug("Image %s not found", remote_name)

        if branch == "master" or not branch_image_exists:
            try:
                remote_name = name
                remote = self._client.images.get_registry_data(remote_name).pull()
                remote_image = {
                    "sha256": remote.id.replace("sha256:", ""),
                    "created": remote.labels["com.exchangeunion.image.created"],
                    "size": remote.attrs["Size"]
                }
                # self._logger.debug("%s: (%s) created at %s, size: %s", remote_name, remote_image["sha256"][:6], remote_image["created"], remote_image["size"])
            except NotFound:
                if not missing:
                    return "local", None
                else:
                    return "not_found", None

        self._logger.debug("Comparing images local_image=%r, remote_image_name=%r, remove_image=%r", local_image, remote_name, remote_image)

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

    def check_updates(self):
        if self._config.disable_update:
            return

        outdated = False

        # Step 1. check all images
        print("🌍 Checking for updates ...")
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
                        self._logger.debug("Checking image: %s: %r" % (image, result))
                    except Exception as e:
                        failed.append((image, e))
                for f in not_done:
                    image = fs[f]
                    failed.append((image, "timeout"))
            if len(failed) > 0:
                print("Failed to check for image updates.")
                for f in failed:
                    print(f"* {f[0]}: {str(f[1])}")
                answer = self._shell.yes_or_no("Try again?")
                if answer == "yes":
                    images = [f[0] for f in failed]
                    continue
                else:
                    raise ImagesCheckAbortion(failed)
            else:
                break

        # TODO handle image local status. Print a warning or give users a choice
        for image, result in images_check_result.items():
            status, pull_image = result
            if status in ["missing", "outdated"]:
                print("* Image %s: %s" % (image, status))
                outdated = True
            elif status == "not_found":
                not_found_images = [img for img, status in images_check_result.items() if status[0] == "not_found"]
                raise ImagesNotAvailable(not_found_images)

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
                        self._logger.debug("Checking container: %s: %r" % (container.container_name, result))
                    except Exception as e:
                        failed.append((container, e))
                for f in not_done:
                    container = fs[f]
                    failed.append((container, "timeout"))
            if len(failed) > 0:
                print("Failed to check for container updates.")
                for f in failed:
                    print(f"* {f[0].name}: {str(f[1])}")
                answer = self._shell.yes_or_no("Try again?")
                if answer == "yes":
                    containers = [f[0] for f in failed]
                    continue
                else:
                    raise ContainersCheckAbortion(failed)
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
            answer = self._shell.yes_or_no("A new version is available. Would you like to upgrade (Warning: this may restart your environment and cancel all open orders)?")

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

    def start_container(self, container):
        try:
            container.start()
            return "done"
        except:
            return "error"

    def ensure_containers(self):
        containers = self._containers.values()
        while len(containers) > 0:
            max_workers = len(containers)
            failed = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                fs = {executor.submit(c.start): c for c in containers}
                done, not_done = wait(fs, 60)
                for f in done:
                    container = fs[f]
                    try:
                        f.result()
                    except Exception as e:
                        failed.append((container, e))
                for f in not_done:
                    container = fs[f]
                    failed.append((container, "timeout"))

            if len(failed) > 0:
                print("Failed to start these containers.")
                for f in failed:
                    print(f"* {f[0].name}: {str(f[1])}")
                answer = self._shell.yes_or_no("Try again?")
                if answer == "yes":
                    containers = [f[0] for f in failed]
                    continue
                else:
                    raise ContainersEnsureAbortion(failed)
            else:
                break

    def no_lnd_wallet(self, lnd):
        while True:
            try:
                info = lnd.api.getinfo()
                break
            except LndApiError as e:
                if "unable to read macaroon path" in str(e):
                    return True
                elif "open /root/.lnd/tls.cert: no such file or directory" in str(e):
                    continue
                elif "Wallet is encrypted" in str(e):
                    return False
            time.sleep(3)
        return False

    def wait_xud(self, xud):
        while True:
            try:
                xud.api.getinfo()
            except XudApiError as e:
                if "UNIMPLEMENTED" in str(e) or "xud is locked" in str(e):
                    break
            time.sleep(3)

    def xucli_create_wrapper(self, xud):
        counter = 0
        ok = False
        while counter < 3:
            try:
                xud.cli("create", self._shell)
                while True:
                    confirmed = self._shell.confirm("YOU WILL NOT BE ABLE TO DISPLAY YOUR XUD SEED AGAIN. Press ENTER to continue...")
                    if confirmed:
                        break
                ok = True
                break
            except (PasswordNotMatch, InvalidPassword):
                counter += 1
                continue
        if not ok:
            raise Exception("Failed to create wallets")

    def xucli_restore_wrapper(self, xud):
        counter = 0
        ok = False
        while counter < 3:
            try:
                if self._config.restore_dir == "/tmp/fake-backup":
                    command = f"restore /tmp/fake-backup /root/.raiden/.xud-backup-raiden-db"
                else:
                    command = f"restore /mnt/hostfs{self._config.restore_dir} /root/.raiden/.xud-backup-raiden-db"
                xud.cli(command, self._shell)
                ok = True
                break
            except (PasswordNotMatch, InvalidPassword, MnemonicNot24Words):
                counter += 1
                continue
        if not ok:
            raise Exception("Failed to restore wallets")

    def check_backup_dir(self, backup_dir):
        hostfs_dir = "/mnt/hostfs" + backup_dir

        if not os.path.exists(hostfs_dir):
            return False, "not existed"

        if not os.path.isdir(hostfs_dir):
            return False, "not a directory"

        if not os.access(hostfs_dir, os.R_OK):
            return False, "not readable"

        if not os.access(hostfs_dir, os.W_OK):
            return False, "not writable"

        return True, None

    def check_restore_dir(self, restore_dir):
        return self.check_backup_dir(restore_dir)

    def check_restore_dir_files(self, restore_dir):
        files = os.listdir("/mnt/hostfs" + restore_dir)
        if "xud" in files:
            return True
        if "lnd-BTC" in files:
            return True
        if "lnd-LTC" in files:
            return True
        if "raiden" in files:
            return True
        return False

    def persist_backup_dir(self, backup_dir):
        network = self.network
        config_file = f"/root/.xud-docker/{network}/{network}.conf"

        exit_code = os.system(f"grep -q backup-dir {config_file} >/dev/null 2>&1")

        if exit_code == 0:
            if not self._config.backup_dir:
                raise NetworkConfigFileSyntaxError(f"The \"backup-dir\" option is in a wrong section of {network}.conf. Please check your configuration file.")
            os.system(f"sed -Ei 's/^.*backup-dir = .*$/backup-dir = {backup_dir}' {config_file}")
        else:
            with open(config_file, 'r') as f:
                contents = f.readlines()
            with open(config_file, 'w') as f:
                f.write("# The path to the directory to store your backup in. This should be located on an external drive, which usually is mounted in /mnt or /media.\n")
                f.write(f"backup-dir = \"{backup_dir}\"\n")
                f.write("\n")
                f.write("".join(contents))

    def setup_backup_dir(self):
        if self._config.backup_dir:
            return

        backup_dir = None

        while True:
            reply = self._shell.input("Enter path to backup location: ")
            reply = reply.strip()
            if len(reply) == 0:
                continue

            backup_dir = self.normalize_path(reply)

            print("Checking backup location... ", end="")
            sys.stdout.flush()
            ok, reason = self.check_backup_dir(backup_dir)
            if ok:
                print("OK.")
                self.persist_backup_dir(backup_dir)
                break
            else:
                print(f"Failed. ", end="")
                self._logger.debug(f"Failed to check backup dir {backup_dir}: {reason}")
                sys.stdout.flush()
                r = self._shell.no_or_yes("Retry?")
                if r == "no":
                    self.command_down()
                    raise BackupDirNotAvailable()

        if self._config.backup_dir != backup_dir:
            self._config.backup_dir = backup_dir

    def is_backup_available(self):
        if self._config.backup_dir is None:
            return False

        ok, reason = self.check_backup_dir(self._config.backup_dir)

        if not ok:
            return False

        return True

    def normalize_path(self, path: str) -> str:
        parts = path.split("/")
        pwd: str = os.environ["HOST_PWD"]
        home: str = os.environ["HOST_HOME"]

        # expand ~
        while "~" in parts:
            i = parts.index("~")
            if i + 1 < len(parts):
                parts = parts[:i] + home.split("/") + parts[i + 1:]
            else:
                parts = parts[:i] + home.split("/")

        if len(parts[0]) > 0:
            parts = pwd.split("/") + parts

        # remove all '.'
        if "." in parts:
            parts.remove(".")

        # remove all '..'
        if ".." in parts:
            parts = [p for i, p in enumerate(parts) if i + 1 < len(parts) and parts[i + 1] != ".." or i + 1 == len(parts)]
            parts.remove("..")

        return "/".join(parts)

    def setup_restore_dir(self):
        if self._config.restore_dir:
            return

        restore_dir = None

        while True:
            reply = self._shell.input("Please paste the path to your XUD backup to restore your channel balance, your keys and other historical data: ")
            reply = reply.strip()
            if len(reply) == 0:
                continue

            restore_dir = self.normalize_path(reply)

            print("Checking files... ", end="")
            sys.stdout.flush()
            ok, reason = self.check_restore_dir(restore_dir)
            if ok:
                if self.check_restore_dir_files(restore_dir):
                    r = self._shell.yes_or_no("Looking good. This will restore xud, lndbtc, raiden. Do you wish to continue?")
                    if r == "yes":
                        break
                    else:
                        restore_dir = "/tmp/fake-backup"
                        break
                else:
                    r = self._shell.yes_or_no("No backup files found. Do you wish to continue WITHOUT restoring channel balance, keys and historical data?")
                    if r == "yes":
                        break
                    else:
                        restore_dir = "/tmp/fake-backup"
                        break
            else:
                print(f"Path not available. ", end="")
                self._logger.debug(f"Failed to check restore dir {restore_dir}: {reason}")
                sys.stdout.flush()
                r = self._shell.yes_or_no("Do you wish to continue WITHOUT restoring channel balance, keys and historical data?")
                if r == "no":
                    raise RestoreDirNotAvailable()

        self._config.restore_dir = restore_dir

    def check_wallets(self):
        lndbtc = self._containers.get("lndbtc")
        lndltc = self._containers.get("lndltc")
        xud = self._containers.get("xud")

        if self.no_lnd_wallet(lndbtc) or self.no_lnd_wallet(lndltc):
            self.wait_xud(xud)

            while True:
                print("Do you want to create a new XUD SEED or restore an existing one?")
                print("1. Create New")
                print("2. Restore Existing")
                reply = self._shell.input("Please choose: ")
                try:
                    if reply == "1":
                        self.xucli_create_wrapper(xud)
                    else:
                        self.setup_restore_dir()
                        r = self._shell.yes_or_no("BEWARE: Restoring your environment will close your existing lnd channels and restore channel balance in your wallet. Do you wish to continue?")
                        if r == "no":
                            raise RestoreCancelled()
                        self.xucli_restore_wrapper(xud)
                    break
                except:
                    pass

            print()
            print("Please enter a path to a destination where to store a backup of your environment. It includes everything, but NOT your wallet balance which is secured by your XUD SEED. The path should be an external drive, like a USB or network drive, which is permanently available on your device since backups are written constantly.")
            print()

            self.setup_backup_dir()
        else:
            if not self.is_backup_available():
                print("Backup location not available.")
                self.setup_backup_dir()

        cmd = f"/update-backup-dir.sh '/mnt/hostfs{self._config.backup_dir}'"
        exit_code, output = self._containers["xud"].exec(cmd)
        lines = output.decode().splitlines()
        if len(lines) > 0:
            print(lines[0])

    def wait_for_channels(self):
        # TODO wait for channels
        pass

    def start(self):
        try:
            self.check_updates()
        except (ImagesCheckAbortion, ContainersCheckAbortion):
            pass

        try:
            self.ensure_containers()
            if self.network in ["testnet", "mainnet"]:
                self.check_wallets()
            elif self.network == "simnet":
                self.wait_for_channels()
        except ContainersEnsureAbortion:
            pass

        self._shell.start(f"{self.network} > ", self.handle_command)


class Launcher:
    def __init__(self):
        self._logger = logging.getLogger("launcher.Launcher")
        self._config = Config()
        self._shell = Shell()

    def launch(self):
        network = os.environ["NETWORK"]
        network_dir = os.environ["NETWORK_DIR"]
        log_timestamp = os.environ["LOG_TIMESTAMP"]
        exit_code = 0
        try:
            self._config.parse()
            self._shell.set_network(network)  # will create shell history file in network_dir
            env = XudEnv(self._config, self._shell)
            env.start()
        except KeyboardInterrupt:
            print()
            exit_code = 2
        except BackupDirNotAvailable:
            exit_code = 3
        except RestoreDirNotAvailable:
            exit_code = 4
        except ImagesNotAvailable as e:
            if len(e.images) == 1:
                print(f"❌ No such image: {e.images[0]}")
            elif len(e.images) > 1:
                images_list = ", ".join(e.images)
                print(f"❌ No such images: {images_list}")
            exit_code = 5
        except NetworkConfigFileSyntaxError as e:
            print(f"❌ {e}")
            exit_code = 6
        except RestoreCancelled:
            exit_code = 7
        except ArgumentError as e:
            print(f"❌ {e}")
            exit_code = 100
        except toml.TomlDecodeError as e:
            print(f"❌ {e}")
            exit_code = 101
        except:
            print(f"❌ Failed to launch {network} environment. For more details, see {network_dir}/{network}-{log_timestamp}.log")
            self._logger.exception("Failed to launch")
            exit_code = 1
        finally:
            self._shell.stop()
        exit(exit_code)
