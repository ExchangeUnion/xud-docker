from .base import Node


class Webui(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)
        self.container_spec.environment.append(f"WEBUI_OPTS={self.options}")

    def status(self):
        return "Ready"
