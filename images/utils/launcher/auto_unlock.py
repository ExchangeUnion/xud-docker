import logging
from .node import XudApiError

logger = logging.getLogger(__name__)


class Action:
    def __init__(self, node_manager):
        self.node_manager = node_manager

    @property
    def shell(self):
        return self.node_manager.shell

    def xud_is_locked(self, xud):
        try:
            info = xud.api.getinfo()
            return False
        except XudApiError as e:
            if "xud is locked" in str(e):
                return True
            return False

    def xucli_unlock_wrapper(self, xud):
        while True:
            try:
                print()
                xud.cli("unlock", self.shell)
                break
            except KeyboardInterrupt:
                break
            except:
                pass

    def execute(self):
        xud = self.node_manager.get_node("xud")
        if not self.xud_is_locked(xud):
            return
        logger.info("Unlock wallets")
        self.xucli_unlock_wrapper(xud)
