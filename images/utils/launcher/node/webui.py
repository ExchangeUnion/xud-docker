from .base import Node


class Webui(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

    def status(self):
        status = super().status()
        if status != "Container running":
            return status

        return "Ready"
