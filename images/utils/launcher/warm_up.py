import logging

from .node import NodeManager


class Action:
    def __init__(self, node_manager: NodeManager):
        self.logger = logging.getLogger("launcher.WarmUpAction")
        self.node_manager = node_manager

    def execute(self):
        print("\n🏃 Warming up...\n")
