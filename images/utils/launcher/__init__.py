import logging
import shlex
import traceback
from threading import Event

from launcher.close_other_utils import Action as CloseOtherUtilsAction
from launcher.config import Config
from launcher.errors import FatalError, ConfigError, ConfigErrorScope, NoWaiting, ParallelError
from launcher.node import NodeManager, ServiceNotFound, ContainerNotFound
from launcher.utils import ArgumentError
import docker.errors
import os

logger = logging.getLogger(__name__)

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

REPORT = """Please click on https://github.com/ExchangeUnion/xud/issues/new?assignees=kilrau&labels=bug&template=bug-\
report.md&title=Short%2C+concise+description+of+the+bug, describe your issue, drag and drop the file "{network}.log" \
which is located in "{logs_dir}" into your browser window and submit your issue."""


class XudEnv:
    def __init__(self, config: Config):
        self.config = config
        self.node_manager = NodeManager(config)

    def handle_command(self, cmd: str) -> None:
        args = shlex.split(cmd)
        arg0 = args[0]
        args = args[1:]

        if arg0 == "help":
            print(HELP)
        elif arg0 == "status":
            self.node_manager.status()
        elif arg0 == "report":
            print(REPORT.format(self.config.network, self.config.logs_dir))
        elif arg0 == "logs":
            self.node_manager.cmd_logs.execute(*args)
        elif arg0 == "start":
            self.node_manager.cmd_start.execute(*args)
        elif arg0 == "stop":
            self.node_manager.cmd_stop.execute(*args)
        elif arg0 == "restart":
            self.node_manager.cmd_restart.execute(*args)
        elif arg0 == "_create":
            self.node_manager.cmd_create.execute(*args)
        elif arg0 == "rm":
            self.node_manager.cmd_remove.execute(*args)
        elif arg0 == "down":
            self.node_manager.down()
        elif arg0 == "up":
            self.node_manager.up()
        elif arg0 == "bitcoin-cli":
            bitcoind = self.node_manager.get_service("bitcoind")
            bitcoind.cli(" ".join(args))
        elif arg0 == "litecoin-cli":
            litecoind = self.node_manager.get_service("litecoind")
            litecoind.cli(" ".join(args))
        elif arg0 == "lndbtc-lncli":
            lndbtc = self.node_manager.get_service("lndbtc")
            lndbtc.cli(" ".join(args))
        elif arg0 == "lndltc-lncli":
            lndltc = self.node_manager.get_service("lndltc")
            lndltc.cli(" ".join(args))
        elif arg0 == "geth":
            geth = self.node_manager.get_service("geth")
            geth.cli(" ".join(args))
        elif arg0 == "xucli":
            xud = self.node_manager.get_service("xud")
            xud.cli(" ".join(args))
        elif arg0 == "boltzcli":
            boltz = self.node_manager.get_service("boltz")
            boltz.cli(" ".join(args))
        elif arg0 == "deposit":
            boltz = self.node_manager.get_service("boltz")
            if len(args) == 0:
                print("Missing chain")
            chain = args[0].lower()
            args = args[1:]
            if chain == "btc":
                boltz.cli("btc deposit " + " ".join(args))
            elif chain == "ltc":
                boltz.cli("ltc deposit " + " ".join(args))
            else:
                xud = self.node_manager.get_service("xud")
                xud.cli("walletdeposit %s %s" % (chain, " ".join(args)))
        elif arg0 == "withdraw":
            boltz = self.node_manager.get_service("boltz")
            if len(args) == 0:
                print("Missing chain")
            chain = args[0].lower()
            args = args[1:]
            if chain == "btc":
                boltz.cli("btc withdraw " + " ".join(args))
            elif chain == "ltc":
                boltz.cli("ltc withdraw " + " ".join(args))
            else:
                xud = self.node_manager.get_service("xud")
                xud.cli("walletwithdraw %s %s" % (chain, " ".join(args)))
        else:
            xud = self.node_manager.get_service("xud")
            xud.cli(cmd)

    def close_other_utils(self):
        CloseOtherUtilsAction(self.config.network).execute()

    def pre_shell(self):
        print("\n🏃 Warming up...\n")

        xud = self.node_manager.get_service("xud")
        stop = Event()
        try:
            # FIXME pty signal only works in main thread
            xud.ensure_ready(stop)
        except (KeyboardInterrupt, NoWaiting):
            stop.set()
            raise

        self.close_other_utils()

    def start(self):
        logger.info("Start %s", self.config.network)

        self.node_manager.update()

        self.node_manager.up()

        self.pre_shell()

        logger.info("Start shell")
        banner_file = os.path.dirname(__file__) + "/banner.txt"
        with open(banner_file) as f:
            print(f.read(), end="", flush=True)
        prompt = f"{self.config.network} > "
        while True:
            try:
                cmd = input(prompt)
                cmd = cmd.strip()
                if cmd == "":
                    continue
                if cmd == "exit":
                    break
                try:
                    self.handle_command(cmd)
                except KeyboardInterrupt:
                    pass
                except ServiceNotFound as e:
                    print("Service not found: %s" % e)
                except ContainerNotFound as e:
                    print("Service not running: %s" % e)
                except docker.errors.APIError as e:
                    print(e)
                except ArgumentError as e:
                    print(e.usage)
                    print(f"Error: {e}")
                except:
                    logger.exception("[Shell] Failed to execute command: %s", cmd)
                    traceback.print_exc()
            except KeyboardInterrupt:
                print()


def print_config_error_cause(e: ConfigError) -> None:
    if e.__cause__:
        cause = str(e.__cause__)
        if cause == "":
            print(type(e.__cause__))
        else:
            print(cause.capitalize())


class Launcher:
    def launch(self):
        config = None
        try:
            config = Config()
            env = XudEnv(config)
            env.start()
        except KeyboardInterrupt:
            print()
            exit(1)
        except NoWaiting:
            exit(1)
        except FatalError as e:
            msg = "💀 %s." % str(e)
            if config:
                msg += " For more details, see %s" % config.host_logfile
            print(msg)
            exit(1)
        except ParallelError:
            if config:
                msg = "For more details, see %s" % config.host_logfile
                print(msg)
            exit(1)
