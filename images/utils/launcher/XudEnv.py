from logging import getLogger
import shlex

from .utils import ArgumentError

from .check_wallets import Action as CheckWalletsAction
from .close_other_utils import Action as CloseOtherUtilsAction
from .auto_unlock import Action as AutoUnlockAction
from .warm_up import Action as WarmUpAction

from .node import NodeManager

__all__ = ["XudEnv"]

logger = getLogger(__name__)


class XudEnv:
    def __init__(self, config, shell):
        self.config = config
        self.shell = shell

        self.node_manager = NodeManager(config, shell)

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
                self.delegate_cmd_to_xucli(cmd)
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
        self.node_manager.update()
        self.node_manager.ensure()
        self.pre_start()
        self.shell.start(f"{self.config.network} > ", self.handle_command)

    def export(self) -> str:
        return self.node_manager.export()
