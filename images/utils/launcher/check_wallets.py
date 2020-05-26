import logging
import sys
import os
from subprocess import check_output
import toml
import docker
import time
from concurrent.futures import ThreadPoolExecutor
from docker.models.containers import Container
from datetime import datetime

from .node import NodeManager
from .node.xud import PasswordNotMatch, InvalidPassword, MnemonicNot24Words
from .utils import normalize_path, get_hostfs_file
from .errors import FatalError
from .types import LndChain, XudNetwork


class Action:
    def __init__(self, node_manager: NodeManager):
        self.logger = logging.getLogger("launcher.CheckWalletsAction")
        self.node_manager = node_manager

    @property
    def shell(self):
        return self.node_manager.shell

    @property
    def config(self):
        return self.node_manager.config

    @property
    def network(self) -> XudNetwork:
        return self.config.network

    def lnd_has_unlock_log_line(self, c):
        pass

    def restart_lnds(self, network: XudNetwork):
        """
        This is temporary solution for lnd unlock stuck problem
        TODO remove it later
        """
        def restart(name):
            client = docker.from_env()
            c = client.containers.get(name)
            c.restart()
            return c

        def stop(name):
            client = docker.from_env()
            c = client.containers.get(name)
            c.stop()
            return c

        def start(name):
            client = docker.from_env()
            c = client.containers.get(name)
            c.start()
            return c

        def xud_restart():
            name = f"{network}_xud_1"

            self.logger.debug("Restarting %s", name)
            c = restart(name)
            self.logger.debug("Restarted %s", name)

            # xud is locked, run 'xucli unlock', 'xucli create', or 'xucli restore' then try again
            for i in range(10):
                exit_code, output = c.exec_run("xucli getinfo")
                result = output.decode()
                if "xud is locked" in result:
                    self.logger.debug("Xud is locked")
                    return
                time.sleep(10)

            raise RuntimeError("Restarted xud should be locked")

        def lnd_restart(chain):
            if chain == "bitcoin":
                name = f"{network}_lndbtc_1"
                short_name = "lndbtc"
            else:
                name = f"{network}_lndltc_1"
                short_name = "lndltc"

            client = docker.from_env()
            c: Container = client.containers.get(name)
            cmd = f"lncli -n {network} -c {chain} getinfo"
            exit_code, output = c.exec_run(cmd)
            self.logger.debug("[Execute] %s: exit_code=%s, output=%s", cmd, exit_code, output)

            if exit_code == 0:
                self.logger.debug("Skip restarting %s", name)
                return

            self.logger.debug("Restarting %s", name)
            c = stop(name)
            t1 = datetime.now()
            c = start(name)
            self.logger.debug("Restarted %s", name)

            # [INF] LTND: Waiting for wallet encryption password. Use `lncli create` to create a wallet, `lncli unlock` to unlock an existing wallet, or `lncli changepassword` to change the password of an existing wallet and unlock it.
            for line in c.logs(stream=True, follow=True, since=t1):
                line = line.decode().strip()
                self.logger.debug("<%s> %s", short_name, line)
                if "Waiting for wallet encryption password" in line:
                    break

            time.sleep(5)
            self.logger.debug("Sleep 5 seconds. For God's sake may lnd work normally!!!")


        with ThreadPoolExecutor(max_workers=3) as executor:
            f1 = executor.submit(lnd_restart, "bitcoin")
            f2 = executor.submit(lnd_restart, "litecoin")

            try:
                f1.result()
            except Exception as e:
                raise RuntimeError("Failed to restart lndbtc") from e

            try:
                f2.result()
            except Exception as e:
                raise RuntimeError("Failed to restart lndltc") from e

            f3 = executor.submit(xud_restart)

            try:
                f3.result()
            except Exception as e:
                raise RuntimeError("Failed to restart xud") from e

    def lnd_ready(self, chain: LndChain) -> bool:
        network = self.node_manager.config.network
        client = docker.from_env()
        if chain == "bitcoin":
            name = f"{network}_lndbtc_1"
        else:
            name = f"{network}_lndltc_1"
        lnd: Container = client.containers.get(name)
        cmd = f"lncli -n {network} -c {chain} getinfo"
        exit_code, output = lnd.exec_run(cmd)
        self.logger.debug("[Execute] %s: exit_code=%s, output=%s", cmd, exit_code, output)
        # [lncli] open /root/.lnd/tls.cert: no such file or directory
        # [lncli] unable to read macaroon path (check the network setting!): open /root/.lnd/data/chain/bitcoin/testnet/admin.macaroon: no such file or directory
        # [lncli] Wallet is encrypted. Please unlock using 'lncli unlock', or set password using 'lncli create' if this is the first time starting lnd.
        return exit_code == 0 or exit_code == 1 and (
                "unable to read macaroon path" in output.decode() or
                "Wallet is encrypted" in output.decode()
        )

    def ensure_lnd_ready(self, chain: LndChain) -> None:
        if chain == "bitcoin":
            name = f"lndbtc"
        else:
            name = f"lndltc"
        for i in range(10):
            if self.lnd_ready(chain):
                self.logger.debug(f"{name.capitalize()} is ready")
                return
            time.sleep(1)
        raise RuntimeError(f"{name.capitalize()} took too long to be ready")

    def ensure_layer2_ready(self) -> None:
        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(self.ensure_lnd_ready, "bitcoin")
            f2 = executor.submit(self.ensure_lnd_ready, "litecoin")

            try:
                f1.result()
            except Exception as e:
                raise FatalError("Failed to ensure lndbtc ready") from e

            try:
                f2.result()
            except Exception as e:
                raise FatalError("Failed to ensure lndltc ready") from e

        client = docker.from_env()
        xud: Container = client.containers.get(f"{self.network}_xud_1")
        cmd = "xucli getinfo -j"

        # Error: ENOENT: no such file or directory, open '/root/.xud/tls.cert'
        # xud is starting... try again in a few seconds
        # xud is locked, run 'xucli unlock', 'xucli create', or 'xucli restore' then try again
        while True:
            exit_code, output = xud.exec_run(cmd)
            self.logger.debug("[Execute] %s: exit_code=%s, output=%s", cmd, exit_code, output)
            if exit_code == 1 and "xud is locked" in output.decode():
                break
            time.sleep(3)
        self.logger.debug("Xud is ready")

    def xucli_create_wrapper(self, xud):
        counter = 0
        ok = False
        while counter < 3:
            try:
                xud.cli("create", self.shell)
                while True:
                    confirmed = self.shell.confirm("YOU WILL NOT BE ABLE TO DISPLAY YOUR XUD SEED AGAIN. Press ENTER to continue...")
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
                if self.config.restore_dir == "/tmp/fake-backup":
                    command = f"restore"
                else:
                    command = f"restore /mnt/hostfs{self.config.restore_dir} /root/.raiden/.xud-backup-raiden-db"
                xud.cli(command, self.shell)
                ok = True
                break
            except (PasswordNotMatch, InvalidPassword, MnemonicNot24Words):
                counter += 1
                continue
        if not ok:
            raise Exception("Failed to restore wallets")

    def check_backup_dir(self, backup_dir):
        hostfs_dir = get_hostfs_file(backup_dir)

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
        files = os.listdir(get_hostfs_file(restore_dir))
        contents = []
        if "xud" in files:
            contents.append("xud")
        if "lnd-BTC" in files:
            contents.append("lndbtc")
        if "lnd-LTC" in files:
            contents.append("lndltc")
        if "raiden" in files:
            contents.append("raiden")
        return contents

    def persist_backup_dir(self, backup_dir):
        network = self.config.network
        config_file = get_hostfs_file(f"{self.config.network_dir}/{network}.conf")

        exit_code = os.system(f"grep -q backup-dir {config_file} >/dev/null 2>&1")

        if exit_code == 0:
            os.system(f"sed -Ei 's|backup-dir = .*$|backup-dir = \"{backup_dir}\"|' {config_file}")
            line = check_output(f"grep backup-dir {config_file}", shell=True).decode().splitlines()[0].strip()
            if line.startswith("#"):
                # uncomment backup-dir line
                os.system(f"sed -Ei 's/^.*#.*backup-dir/backup-dir/' {config_file}")
            try:
                parsed = toml.load(open(config_file))
            except:
                raise RuntimeError(f"Failed to update backup-dir value in {config_file}")
            if "backup-dir" not in parsed:
                raise FatalError(f"The field \"backup-dir\" is in a wrong section of {network}.conf.")
            if parsed["backup-dir"] != backup_dir:
                raise RuntimeError(f"Failed to update backup-dir value in {config_file}")
        else:
            with open(config_file, 'r') as f:
                contents = f.readlines()
            with open(config_file, 'w') as f:
                f.write("# The path to the directory to store your backup in. This should be located on \n# an external drive, which usually is mounted in /mnt or /media.\n")
                f.write(f"backup-dir = \"{backup_dir}\"\n")
                f.write("\n")
                f.write("".join(contents))

    def setup_backup_dir(self):
        if self.config.backup_dir:
            return

        backup_dir = None

        while True:
            reply = self.shell.input("Enter path to backup location: ")
            reply = reply.strip()
            if len(reply) == 0:
                continue

            backup_dir = normalize_path(reply)

            print("Checking backup location... ", end="")
            sys.stdout.flush()
            ok, reason = self.check_backup_dir(backup_dir)
            if ok:
                print("OK.")
                self.persist_backup_dir(backup_dir)
                break
            else:
                print(f"Failed. ", end="")
                self.logger.debug(f"Failed to check backup dir {backup_dir}: {reason}")
                sys.stdout.flush()
                r = self.shell.no_or_yes("Retry?")
                if r == "no":
                    self.node_manager.down()
                    raise FatalError("Backup directory not available")

        if self.config.backup_dir != backup_dir:
            self.config.backup_dir = backup_dir

    def is_backup_available(self):
        if self.config.backup_dir is None:
            return False

        ok, reason = self.check_backup_dir(self.config.backup_dir)

        if not ok:
            return False

        return True

    def setup_restore_dir(self) -> None:
        """This function will try to interactively setting up restore_dir. And
        store it in self._config.restore_dir

        :return: None
        """
        if self.config.restore_dir:
            return

        restore_dir = None

        while True:
            reply = self.shell.input("Please paste the path to your XUD backup to restore your channel balance, your keys and other historical data: ")
            reply = reply.strip()
            if len(reply) == 0:
                continue

            restore_dir = normalize_path(reply)

            print("Checking files... ", end="")
            sys.stdout.flush()
            ok, reason = self.check_restore_dir(restore_dir)
            if ok:
                contents = self.check_restore_dir_files(restore_dir)
                if len(contents) > 0:
                    if len(contents) > 1:
                        contents_text = ", ".join(contents[:-1]) + " and " + contents[-1]
                    else:
                        contents_text = contents[0]
                    r = self.shell.yes_or_no(f"Looking good. This will restore {contents_text}. Do you wish to continue?")
                    if r == "yes":
                        break
                    else:
                        restore_dir = None
                        break
                else:
                    r = self.shell.yes_or_no("No backup files found. Do you wish to continue WITHOUT restoring channel balance, keys and historical data?")
                    if r == "yes":
                        restore_dir = "/tmp/fake-backup"
                        break
            else:
                print(f"Path not available. ", end="")
                self.logger.info(f"Failed to check restore dir {restore_dir}: {reason}")
                sys.stdout.flush()
                r = self.shell.yes_or_no("Do you wish to continue WITHOUT restoring channel balance, keys and historical data?")
                if r == "yes":
                    restore_dir = "/tmp/fake-backup"
                    break

        self.config.restore_dir = restore_dir

    def execute(self):
        xud = self.node_manager.get_node("xud")
        self.ensure_layer2_ready()
        if self.node_manager.newly_installed:
            while True:
                print("Do you want to create a new xud environment or restore an existing one?")
                print("1) Create New")
                print("2) Restore Existing")
                reply = self.shell.input("Please choose: ")
                reply = reply.strip()
                if reply == "1":
                    try:
                        self.xucli_create_wrapper(xud)
                        break
                    except:
                        pass
                elif reply == "2":
                    self.setup_restore_dir()
                    if self.config.restore_dir:
                        if self.config.restore_dir != "/tmp/fake-backup":
                            r = self.shell.yes_or_no("BEWARE: Restoring your environment will close your existing lnd channels and restore channel balance in your wallet. Do you wish to continue?")
                            if r == "yes":
                                try:
                                    self.xucli_restore_wrapper(xud)
                                    break
                                except:
                                    pass
                        else:
                            try:
                                self.xucli_restore_wrapper(xud)
                                break
                            except:
                                pass

                    self.config.restore_dir = None

            if not self.is_backup_available():
                print()
                print("Please enter a path to a destination where to store a backup of your environment. It includes everything, but NOT your wallet balance which is secured by your XUD SEED. The path should be an external drive, like a USB or network drive, which is permanently available on your device since backups are written constantly.")
                print()
                self.config.backup_dir = None
                self.setup_backup_dir()

            if self.network in ["simnet", "testnet", "mainnet"]:
                print("\nClient restart required. This could take up to 3 minutes and you will be prompted to re-enter your password. Restarting...", end="")
                sys.stdout.flush()
                try:
                    self.restart_lnds(self.network)
                    print(" Done.")
                except:
                    self.logger.exception("Failed to do restaring logic here")
                    print(" Failed.")
        else:
            if not self.is_backup_available():
                print("Backup location not available.")
                self.config.backup_dir = None
                self.setup_backup_dir()

        cmd = f"/update-backup-dir.sh '{get_hostfs_file(self.config.backup_dir)}'"
        exit_code, output = xud.exec(cmd)
        lines = output.decode().splitlines()
        if len(lines) > 0:
            print(lines[0])
