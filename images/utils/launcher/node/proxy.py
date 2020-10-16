from .base import Node


class Proxy(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

    def status(self):
        return "Ready"
