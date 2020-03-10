import logging
from .shell import Shell
import shlex
import toml
from shutil import copyfile
import traceback

from .config import Config, ArgumentError, InvalidHomeDir, InvalidNetworkDir
from .node import NodeManager, NodeNotFound, ImagesNotAvailable
from .check_wallets import Action as CheckWalletsAction, BackupDirNotAvailable, NetworkConfigFileSyntaxError
from .utils import ParallelExecutionError


def init_logging():
    fmt = "%(asctime)s.%(msecs)03d %(levelname)s %(process)d --- [%(threadName)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(format=fmt, datefmt=datefmt, level=logging.ERROR, filename="/var/log/launcher.log")

    level_config = {
        "launcher": logging.DEBUG,
    }

    for logger, level in level_config.items():
        logging.getLogger(logger).setLevel(level)


init_logging()


class XudEnv:
    def __init__(self, config: Config, shell: Shell):
        self.logger = logging.getLogger("launcher.XudEnv")

        self.config = config
        self.shell = shell

        self.node_manager = NodeManager(self.config, self.shell)

    def delegate_cmd_to_xucli(self, cmd):
        self.node_manager.get_node("xud").cli(cmd, self.shell)

    def command_report(self):
        network_dir = f"{self.config.home_dir}/{self.config.network}"
        print(f"""Please click on https://github.com/ExchangeUnion/xud/issues/\
new?assignees=kilrau&labels=bug&template=bug-report.md&title=Short%2C+concise+\
description+of+the+bug, describe your issue, drag and drop the file "xud-docker\
.log" which is located in "{network_dir}" into your browser window and submit \
your issue.""")

    def handle_command(self, cmd):
        try:
            args = shlex.split(cmd)
            arg0 = args[0]
            args = args[1:]
            if arg0 == "status":
                self.node_manager.status()
            elif arg0 == "report":
                self.command_report()
            elif arg0 == "logs":
                self.node_manager.logs(*args)
            elif arg0 == "start":
                self.node_manager.start(*args)
            elif arg0 == "stop":
                self.node_manager.stop(*args)
            elif arg0 == "restart":
                self.node_manager.restart(*args)
            elif arg0 == "down":
                self.node_manager.down()
            elif arg0 == "up":
                self.node_manager.up()
            elif arg0 == "btcctl":
                self.node_manager.cli("btcd", *args)
            elif arg0 == "ltcctl":
                self.node_manager.cli("ltcd", *args)
            elif arg0 == "bitcoin-cli":
                self.node_manager.cli("bitcoind", *args)
            elif arg0 == "litecoin-cli":
                self.node_manager.cli("litecoind", *args)
            elif arg0 == "lndbtc-lncli":
                self.node_manager.cli("lndbtc", *args)
            elif arg0 == "lndltc-lncli":
                self.node_manager.cli("lndltc", *args)
            elif arg0 == "geth":
                self.node_manager.cli("geth", *args)
            elif arg0 == "xucli":
                self.node_manager.cli("xud", *args)
            else:
                self.delegate_cmd_to_xucli(cmd)
        except NodeNotFound as e:
            print(f"Node not found: {e}")
        except ArgumentError as e:
            print(e.usage)
            print(f"error: {e}")

    def check_wallets(self):
        CheckWalletsAction(self.node_manager).execute()

    def wait_for_channels(self):
        # TODO wait for channels
        pass

    def pre_start(self):
        if self.config.network in ["testnet", "mainnet"]:
            self.check_wallets()
        elif self.config.network == "simnet":
            self.wait_for_channels()

    def start(self):
        try:
            self.node_manager.update()
        except ParallelExecutionError:
            pass
        self.node_manager.up()
        self.pre_start()
        self.shell.start(f"{self.config.network} > ", self.handle_command)


class Launcher:
    def __init__(self):
        self.logger = logging.getLogger("launcher.Launcher")
        self.logfile = None

    def launch(self):
        sh = Shell()
        exit_code = 0
        cfg = None
        try:
            cfg = Config()
            cfg.parse()
            sh.set_network_dir(cfg.network_dir)  # will create shell history file in network_dir
            env = XudEnv(cfg, sh)
            env.start()
        except KeyboardInterrupt:
            print()
            exit_code = 2
        except BackupDirNotAvailable:
            exit_code = 3
        except (InvalidHomeDir, InvalidNetworkDir) as e:
            print(f"❌ {e}")
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
        except ArgumentError as e:
            print(f"❌ {e}")
            exit_code = 100
        except toml.TomlDecodeError as e:
            print(f"❌ {e}")
            exit_code = 101
        except:
            self.logger.exception("Failed to launch")
            if cfg and cfg.logfile:
                copyfile("/var/log/launcher.log", cfg.logfile)
                logfile = cfg.logfile.replace("/mnt/hostfs", "")
                print(f"❌ Failed to launch {cfg.network} environment. For more details, see {logfile}")
                traceback.print_exc()
            else:
                traceback.print_exc()
            exit_code = 1
        finally:
            sh.stop()
        exit(exit_code)

