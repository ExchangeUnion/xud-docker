import logging
import shlex
import traceback
import os

from .config import Config, ConfigLoader
from .shell import Shell
from .node import NodeManager, NodeNotFound
from .utils import ParallelExecutionError, ArgumentError

from .check_wallets import Action as CheckWalletsAction
from .close_other_utils import Action as CloseOtherUtilsAction
from .auto_unlock import Action as AutoUnlockAction
from .warm_up import Action as WarmUpAction
from .errors import FatalError, ConfigError, ConfigErrorScope


HELP = """\
Xucli shortcut commands
  addcurrency <currency>                    add a currency
  <swap_client> [decimal_places]
  [token_address]
  addpair <pair_id|base_currency>           add a trading pair
  [quote_currency]
  ban <node_identifier>                     ban a remote node
  buy <quantity> <pair_id> <price>          place a buy order
  [order_id]
  closechannel <currency>                   close any payment channels with a
  [node_identifier ] [--force]              peer
  connect <node_uri>                        connect to a remote node
  create                                    create a new xud instance and set a
                                            password
  discovernodes <node_identifier>           discover nodes from a specific peer
  getbalance [currency]                     get total balance for a given
                                            currency
  getinfo                                   get general info from the local xud
                                            node
  getnodeinfo <node_identifier>             get general information about a
                                            known node
  listcurrencies                            list available currencies
  listorders [pair_id] [owner]              list orders from the order book
  [limit]
  listpairs                                 get order book's available pairs
  listpeers                                 list connected peers
  openchannel <currency> <amount>           open a payment channel with a peer
  [node_identifier] [push_amount]
  orderbook [pair_id] [precision]           display the order book, with orders
                                            aggregated per price point
  removecurrency <currency>                 remove a currency
  removeorder <order_id> [quantity]         remove an order
  removepair <pair_id>                      remove a trading pair
  restore [backup_directory]                restore an xud instance from seed
  sell <quantity> <pair_id> <price>         place a sell order
  [order_id]
  shutdown                                  gracefully shutdown local xud node
  streamorders [existing]                   stream order added, removed, and
                                            swapped events (DEMO)
  tradehistory [limit]                      list completed trades
  tradinglimits [currency]                  trading limits for a given currency
  unban <node_identifier>                   unban a previously banned remote
  [--reconnect]                             node
  unlock                                    unlock local xud node
  walletdeposit <currency>                  gets an address to deposit funds to
                                            xud
  walletwithdraw [amount] [currency]        withdraws on-chain funds from xud
  [destination] [fee]
  
General commands
  status                                    show service status
  report                                    report issue
  logs                                      show service log
  start                                     start service
  stop                                      stop service
  restart                                   restart service
  down                                      shutdown the environment
  up                                        bring up the environment
  help                                      show this help
  exit                                      exit xud-ctl shell

CLI commands
  bitcoin-cli                               bitcoind cli
  litecoin-cli                              litecoind cli
  lndbtc-lncli                              lnd cli
  lndltc-lncli                              lnd cli
  geth                                      geth cli
  xucli                                     xud cli
  boltzcli                                  boltz cli

Boltzcli shortcut commands  
  deposit <chain> deposit 
  --inbound [inbound_balance]               deposit from boltz (btc/ltc)
  boltzcli <chain> withdraw 
  <amount> <address>                        withdraw from boltz channel
  
"""


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
    def __init__(self, config, shell):
        self.logger = logging.getLogger("launcher.XudEnv")

        self.config = config
        self.shell = shell

        self.node_manager = NodeManager(config, shell)

    def delegate_cmd_to_xucli(self, cmd):
        self.node_manager.get_node("xud").cli(cmd, self.shell)

    def command_report(self):
        logs_dir = f"{self.config.home_dir}/{self.config.network}/logs"
        print(f"""Please click on https://github.com/ExchangeUnion/xud/issues/\
new?assignees=kilrau&labels=bug&template=bug-report.md&title=Short%2C+concise+\
description+of+the+bug, describe your issue, drag and drop the file "{self.config.network}\
.log" which is located in "{logs_dir}" into your browser window and submit \
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
            elif arg0 == "boltzcli":
                self.node_manager.cli("boltz", *args)
            elif arg0 == "deposit":
                if len(args) == 0:
                    print("Missing chain")
                chain = args[0]
                args = args[1:]
                if chain == "btc":
                    self.node_manager.cli("boltz", "btc", "deposit", *args)
                elif chain == "ltc":
                    self.node_manager.cli("boltz", "ltc", "deposit", *args)
                else:
                    self.node_manager.cli("xud", "walletdeposit", chain, *args)
            elif arg0 == "withdraw":
                if len(args) == 0:
                    print("Missing chain")
                chain = args[0]
                args = args[1:]
                if chain == "btc":
                    self.node_manager.cli("boltz", "btc", "withdraw", *args)
                elif chain == "ltc":
                    self.node_manager.cli("boltz", "ltc", "withdraw", *args)
                else:
                    self.node_manager.cli("xud", "walletwithdraw", chain, *args)
            elif arg0 == "help":
                print(HELP)
            else:
                self.delegate_cmd_to_xucli(cmd)

        except NodeNotFound as e:
            if str(e) == "boltz" and self.config.network == "simnet":
                print("Not available on simnet")
                return

            print(f"Node not found: {e}")
        except ArgumentError as e:
            print(e.usage)
            print(f"error: {e}")

    def check_wallets(self):
        CheckWalletsAction(self.node_manager).execute()

    def wait_for_channels(self):
        # TODO wait for channels
        pass

    def auto_unlock(self):
        AutoUnlockAction(self.node_manager).execute()

    def close_other_utils(self):
        CloseOtherUtilsAction(self.config.network, self.shell).execute()

    def warm_up(self):
        WarmUpAction(self.node_manager).execute()

    def pre_start(self):
        self.warm_up()
        self.check_wallets()

        if self.config.network == "simnet":
            self.wait_for_channels()

        self.auto_unlock()

        self.close_other_utils()

    def start(self):
        up_env = True
        try:
            up_env = self.node_manager.update()
        except ParallelExecutionError:
            pass

        if up_env:
            self.node_manager.up()
            self.pre_start()

        self.shell.start(f"{self.config.network} > ", self.handle_command)


def print_config_error_cause(e: ConfigError) -> None:
    if e.__cause__:
        cause = str(e.__cause__)
        if cause == "":
            print(type(e.__cause__))
        else:
            print(cause.capitalize())


class Launcher:
    def __init__(self):
        self.logger = logging.getLogger("launcher.Launcher")
        self.logfile = None

    def launch(self):
        shell = Shell()
        config = None
        try:
            config = Config(ConfigLoader())
            assert config.network_dir is not None
            shell.set_network_dir(config.network_dir)  # will create shell history file in network_dir
            env = XudEnv(config, shell)
            env.start()
        except KeyboardInterrupt:
            print()
        except ConfigError as e:
            if e.scope == ConfigErrorScope.COMMAND_LINE_ARGS:
                print("Failed to parse command-line arguments, exiting.")
                print_config_error_cause(e)
            elif e.scope == ConfigErrorScope.GENERAL_CONF:
                print("Failed to parse config file {}, exiting.".format(e.conf_file))
                print_config_error_cause(e)
            elif e.scope == ConfigErrorScope.NETWORK_CONF:
                print("Failed to parse config file {}, exiting.".format(e.conf_file))
                print_config_error_cause(e)
        except FatalError as e:
            if config and config.logfile:
                print("{}. For more details, see {}".format(e, config.logfile))
            else:
                traceback.print_exc()
        except Exception:  # exclude system exceptions like SystemExit
            self.logger.exception("Unexpected exception during launching")
            traceback.print_exc()
        finally:
            shell.stop()

