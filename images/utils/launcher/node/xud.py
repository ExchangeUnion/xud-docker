from __future__ import annotations

import functools
import json
import logging
import os
import re
from concurrent.futures import wait, TimeoutError
import threading
from typing import List, Optional
import docker.errors

from launcher.table import ServiceTable
from launcher.utils import yes_or_no, normalize_path
from launcher.errors import NoWaiting, FatalError
from .base import Node, CliBackend, CliError
from .lnd import CFHeaderState

logger = logging.getLogger(__name__)


class XudApiError(Exception):
    pass


class XudApi:
    def __init__(self, backend):
        self._backend = backend

    def getinfo(self):
        try:
            s = self._backend.invoke("getinfo -j")
            return json.loads(s)
        except CliError as e:
            raise XudApiError(e.output)


class InvalidPassword(Exception):
    pass


class PasswordNotMatch(Exception):
    pass


class WrongPassword(Exception):
    pass


class MnemonicNot24Words(Exception):
    pass


class NoWalletsInitialized(Exception):
    pass


class Cancelled(Exception):
    pass


class InvalidDirectory(Exception):
    pass


class Xud(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        self.container_spec.environment.extend(self._get_environment())

        self._cli = "xucli"

        self.api = XudApi(CliBackend(self.name, self.container_name, self._cli))

    def _get_environment(self) -> List[str]:
        env = [
            "NODE_ENV=production"
        ]

        lndbtc = self.config.nodes["lndbtc"]
        if lndbtc["mode"] == "external":
            env.extend([
                "LNDBTC_RPC_HOST={}".format(lndbtc["rpc_host"]),
                "LNDBTC_RPC_PORT={}".format(lndbtc["rpc_port"]),
                "LNDBTC_CERTPATH={}".format(lndbtc["certpath"]),
                "LNDBTC_MACAROONPATH={}".format(lndbtc["macaroonpath"]),
            ])

        lndltc = self.config.nodes["lndltc"]
        if lndltc["mode"] == "external":
            env.extend([
                "LNDLTC_RPC_HOST={}".format(lndbtc["rpc_host"]),
                "LNDLTC_RPC_PORT={}".format(lndbtc["rpc_port"]),
                "LNDLTC_CERTPATH={}".format(lndbtc["certpath"]),
                "LNDLTC_MACAROONPATH={}".format(lndbtc["macaroonpath"]),
            ])

        if "debug" in self.node_config:
            debug_port = self.node_config["debug"]
            if debug_port:
                env.append(f"DEBUG_PORT={debug_port}")

        return env

    def status(self):
        status = super().status()
        if status != "Container running":
            return status
        try:
            info = self.api.getinfo()
            lndbtc_status = info["lndMap"][0][1]["status"]
            lndltc_status = info["lndMap"][1][1]["status"]
            connext_status = info["connext"]["status"]

            if "Ready" == lndbtc_status \
                    or "Ready" == lndltc_status \
                    or "Ready" == connext_status:
                return "Ready"

            if "has no active channels" in lndbtc_status \
                    or "has no active channels" in lndltc_status \
                    or "has no active channels" in connext_status:
                return "Waiting for channels"
            else:
                not_ready = []
                if lndbtc_status != "Ready":
                    not_ready.append("lndbtc")
                if lndltc_status != "Ready":
                    not_ready.append("lndltc")
                if connext_status != "Ready":
                    not_ready.append("connext")
                return "Waiting for " + ", ".join(not_ready)
        except XudApiError as e:
            if "xud is locked" in str(e):
                return "Wallet locked. Unlock with xucli unlock."
            elif "no such file or directory, open '/root/.xud/tls.cert'" in str(e):
                return "Starting..."
            elif "xud is starting" in str(e):
                return "Starting..."
            else:
                return str(e)
        except:
            self._logger.exception("Failed to get advanced running status")
            return "Waiting for xud to come up..."

    def cli_filter(self, cmd, text):
        text = re.sub(r"D.*Warning: insecure environment read function 'getenv' used[\s\n\r]+", "", text)
        return text

    def extract_exception(self, cmd: str, output: str):
        if cmd.startswith("create"):
            if "password must be at least 8 characters" in output:
                raise InvalidPassword
            elif "Passwords do not match, please try again" in output:
                raise PasswordNotMatch
            elif "xud was initialized without a seed because no wallets could be initialized" in output:
                raise NoWalletsInitialized
            elif "Error: " in output:
                raise FatalError("Failed to create wallets")
            elif "it is your ONLY backup in case of data loss" in output:
                return
            else:
                print("^C")
                raise KeyboardInterrupt
        elif cmd.startswith("restore"):
            if "Password must be at least 8 characters" in output:
                raise InvalidPassword
            elif "Passwords do not match, please try again" in output:
                raise PasswordNotMatch
            elif "Mnemonic must be exactly 24 words" in output:
                raise MnemonicNot24Words
            elif "Error: " in output:
                raise FatalError("Failed to restore wallets")
            elif "The following wallets were restored" in output:
                return
            else:
                print("^C")
                raise KeyboardInterrupt
        elif cmd.startswith("unlock"):
            if "xud was unlocked successfully" in output:
                return
            elif "password is incorrect" in output:
                raise WrongPassword
            elif "Error: " in output:
                raise FatalError("Failed to unlock wallets")
            else:
                print("^C")
                raise KeyboardInterrupt()

    def _ensure_dependencies_ready(self, stop: threading.Event):
        deps = [
            self.get_service("lndbtc"),
            self.get_service("lndltc"),
            self.get_service("connext"),
        ]

        executor = self.config.executor

        futs = {executor.submit(getattr(d, "ensure_ready"), stop): d for d in deps}

        while True:
            done, not_done = wait(futs, 30)
            if len(not_done) == 0:
                break
            names = [futs[f].name for f in not_done]
            names_str = ", ".join(names)
            reply = yes_or_no("Keep waiting for {} to be ready?".format(names_str))
            if reply == "no":
                raise NoWaiting

    def _save_seed(self, output):
        s = output
        p1 = re.compile(r"^.*BEGIN XUD SEED-+([^-]+)-+END XUD SEED.*$", re.MULTILINE | re.DOTALL)
        m = p1.match(s)
        s = m.group(1)
        p2 = re.compile(r"\s*\d+\.\s*")
        s = re.sub(p2, " ", s)
        s = s.strip()

        seed_file = os.path.join(self.config.network_dir, "seed.txt")
        with open(seed_file, "w") as f:
            f.write(s)

        print(f"[DEV] XUD seed is saved in file {self.config.host_network_dir}/seed.txt")

    def _create_wallets(self) -> None:
        retry = 3
        i = 0
        while i < retry:
            try:
                if self.config.dev_mode:
                    self.cli("create", exception=True, parse_output=self._save_seed)
                else:
                    self.cli("create", exception=True)
                input("YOU WILL NOT BE ABLE TO DISPLAY YOUR XUD SEED AGAIN. Press ENTER to continue...")
                return
            except (PasswordNotMatch, InvalidPassword):
                pass
            i += 1
        raise Cancelled

    def _check_restore_dir(self, value) -> List[str]:
        try:
            self._check_backup_dir(value)
        except Exception as e:
            raise Exception("Path not available ({})".format(e)) from e

        files = os.listdir("/mnt/hostfs" + value)
        contents = []
        if "xud" in files:
            contents.append("xud")
        if "lnd-BTC" in files:
            contents.append("lndbtc")
        if "lnd-LTC" in files:
            contents.append("lndltc")

        if len(contents) > 0:
            return contents
        else:
            raise Exception("No backup files found")

    def _get_restore_dir(self) -> str:
        restore_dir = self.config.restore_dir

        if restore_dir:
            try:
                self._check_backup_dir(restore_dir)
                return restore_dir
            except InvalidDirectory:
                restore_dir = None
                logger.exception("config.restore_dir is not valid")

        while True:
            reply = input("Please paste the path to your XUD backup to restore your channel balance, your keys and other historical data: ")
            reply = reply.strip()
            path = normalize_path(reply)
            print("Checking files... ", end="", flush=True)
            try:
                contents = self._check_restore_dir(path)
            except InvalidDirectory as e:
                print("{}. ".format(e), end="", flush=True)
                reply = yes_or_no("Do you wish to continue WITHOUT restoring channel balance, keys and historical data?")
                if reply == "yes":
                    restore_dir = ""
                    break
                continue

            if len(contents) > 1:
                contents_text = ", ".join(contents[:-1]) + " and " + contents[-1]
            else:
                contents_text = contents[0]
            print(f"Looking good. This will restore {contents_text}. ", end="", flush=True)
            reply = yes_or_no("Do you wish to continue?")
            if reply == "no":
                raise Cancelled
            restore_dir = path
            break

        return restore_dir

    def _restore_wallets(self) -> None:
        restore_dir = self._get_restore_dir()

        retry = 3
        i = 0
        while i < retry:
            try:
                if restore_dir == "":
                    self.cli("restore", exception=True)
                else:
                    self.cli("restore /mnt/hostfs{}".format(restore_dir), exception=True)
                return
            except (PasswordNotMatch, InvalidPassword, MnemonicNot24Words):
                pass
            i += 1
        raise Cancelled

    def _setup_wallets(self) -> None:
        while True:
            print("Do you want to create a new xud environment or restore an existing one?")
            print("1) Create New")
            print("2) Restore Existing")
            reply = input("Please choose: ")
            reply = reply.strip()
            if reply == "1":
                try:
                    self._create_wallets()
                    break
                except Cancelled:
                    continue
            elif reply == "2":
                try:
                    self._restore_wallets()
                    break
                except Cancelled:
                    continue

    @property
    def backup_dir(self) -> Optional[str]:
        value_file = os.path.join(self.data_dir, ".backup-dir-value")
        if os.path.exists(value_file):
            with open(value_file) as f:
                value = f.read().strip()
                value = value.replace("/mnt/hostfs", "")
                return value
        return None

    def update_backup_dir(self, value: str) -> None:
        cmd = "/update-backup-dir.sh '/mnt/hostfs{}'".format(value)
        exit_code, output = self.exec(cmd)
        print(output)
        if exit_code != 0:
            raise Exception("Failed to update backup location")

    def _check_backup_dir(self, value: str) -> None:
        value = "/mnt/hostfs" + value

        if not os.path.exists(value):
            raise InvalidDirectory("not existed")

        if not os.path.isdir(value):
            raise InvalidDirectory("not a directory")

        if not os.access(value, os.R_OK):
            raise InvalidDirectory("not readable")

        if not os.access(value, os.W_OK):
            raise InvalidDirectory("not writable")

    def _setup_backup(self) -> None:
        logger.info("Setup backup")

        current_backup_dir = self.backup_dir

        if current_backup_dir:
            backup_dir = self.config.backup_dir

            if backup_dir:
                if current_backup_dir != backup_dir:
                    self.update_backup_dir(backup_dir)
        else:
            backup_dir = self.config.backup_dir

            if not backup_dir:
                print()
                print("Please enter a path to a destination where to store a backup of your environment. "
                      "It includes everything, but NOT your wallet balance which is secured by your XUD SEED. "
                      "The path should be an external drive, like a USB or network drive, which is permanently "
                      "available on your device since backups are written constantly.")
                print()

                while True:
                    reply = input("Enter path to backup location: ")
                    reply = reply.strip()
                    path = normalize_path(reply)
                    print("Checking backup location... ", end="", flush=True)
                    try:
                        self._check_backup_dir(path)
                        print("OK.")
                    except InvalidDirectory as e:
                        print("Failed (%s)." % e)
                        continue

                    self.update_backup_dir(path)
                    break

            else:
                if current_backup_dir != backup_dir:
                    self.update_backup_dir(backup_dir)

    def has_wallets(self) -> bool:
        nodekey = os.path.join(self.data_dir, "nodekey.dat")
        return os.path.exists(nodekey)

    def _is_locked(self) -> bool:
        try:
            self.api.getinfo()
        except XudApiError as e:
            if "xud is locked" in str(e):
                return True
        return False

    def _unlock(self) -> None:
        logger.info("Unlock wallets")
        self.cli("unlock")

    def _ensure_lnds_synced(self, stop):
        lnds = {}
        lndbtc = self.get_service("lndbtc")
        lndltc = self.get_service("lndltc")
        if lndbtc.mode == "native" and \
                (self.network == "simnet" or self.get_service("bitcoind").mode in ["neutrino", "light"]):
            lnds[lndbtc] = CFHeaderState()
        if lndltc.mode == "native" and \
                (self.network == "simnet" or self.get_service("litecoind").mode in ["neutrino", "light"]):
            lnds[lndltc] = CFHeaderState()

        if len(lnds) > 0:
            def all_ready():
                nonlocal lnds

                return functools.reduce(lambda r, item: r and item.ready, lnds.values(), True)

            def print_syncing(stop: threading.Event):
                nonlocal lnds

                print("Syncing light clients:")

                rows = {}
                for lnd, state in lnds.items():
                    rows[lnd.name] = state.message

                print("%s" % ServiceTable(rows))

                n = len(rows)

                while not stop.is_set():
                    i = 0
                    logger.debug("lnds %r", lnds)
                    for lnd, state in lnds.items():
                        old_msg = rows[lnd.name]
                        msg = state.message
                        if old_msg != msg:
                            if len(old_msg) > len(msg):
                                fmt = "%%%ds" % len(old_msg)
                                msg = fmt % msg
                            y = (n - i) * 2
                            x = 12
                            update = "\033[%dA\033[%dC%s\033[%dD\033[%dB" % (y, x, msg, x + len(msg), y)
                            print(update, end="", flush=True)
                        i += 1

                    if all_ready():
                        break

                    stop.wait(1)

                logger.debug("Light clients syncing ends")

            executor = self.config.executor

            f = executor.submit(print_syncing, stop)

            for lnd in lnds:
                executor.submit(lnd.update_cfheader, lnds[lnd], stop)

            f.result()
            logger.debug("print_syncing ends")

    def _wait_tls_cert(self, stop: threading.Event):
        tls_file = os.path.join(self.data_dir, "tls.cert")
        while not stop.is_set():
            if os.path.exists(tls_file):
                break
            stop.wait(1)

    def _wait_xud_ready(self, stop: threading.Event):
        # Error: ENOENT: no such file or directory, open '/root/.xud/tls.cert'
        # xud is starting... try again in a few seconds
        # xud is locked, run 'xucli unlock', 'xucli create', or 'xucli restore' then try again
        cmd = self._cli + " getinfo -j"
        while not stop.is_set():
            try:
                if not self.is_running:
                    raise FatalError("XUD container \"%s\" stopped unexpectedly" % self.container_name)
                exit_code, output = self.exec(cmd)
                if exit_code == 0:
                    break
                if "xud is locked" in output:
                    break
                logger.debug("[Execute] %s (exit_code=%s)\n%s", cmd, exit_code, output.rstrip())
            except docker.errors.APIError:
                logger.exception("Failed to getinfo")
            stop.wait(1)

    def ensure_ready(self, stop: threading.Event):
        logger.info("Ensuring XUD is ready")

        if self.node_manager.newly_installed:
            logger.info("Ensuring LNDs are synced (light)")
            self._ensure_lnds_synced(stop)

        logger.info("Ensuring XUD dependencies are ready (lndbtc, lndltc and connext)")
        self._ensure_dependencies_ready(stop)

        logger.info("Waiting for XUD to be ready")
        executor = self.config.executor

        f = executor.submit(self._wait_tls_cert, stop)
        while not stop.is_set():
            logger.info("Waiting for XUD tls.cert to be created")
            try:
                f.result(30)
                break
            except TimeoutError:
                print("XUD should not take so long to create \"tls.cert\" file. please check container \"%s\" logs for more details." % self.container_name)
                reply = yes_or_no("Would you like to keep waiting?")
                if reply == "no":
                    raise NoWaiting

        f = executor.submit(self._wait_xud_ready, stop)
        while not stop.is_set():
            logger.info("Waiting for XUD to be ready")
            try:
                f.result(10)
                break
            except TimeoutError:
                print("XUD should not take so long to be ready. please check container \"%s\" logs for more details." % self.container_name)
                reply = yes_or_no("Would you like to keep waiting?")
                if reply == "no":
                    raise NoWaiting

        if not self.has_wallets():
            logger.info("Setting up XUD wallets")
            self._setup_wallets()

        logger.info("Setting up XUD backup")
        self._setup_backup()

        if self._is_locked():
            logger.info("Unlock XUD")
            self._unlock()
