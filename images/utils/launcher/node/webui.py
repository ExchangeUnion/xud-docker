from .base import Node


class Webui(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        self._cli = None
        self.api = None

    def status(self):
        return "Ready"
