from tools.core import src


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__("https://github.com/bitcoin/bitcoin")

    def get_ref(self, version):
        if version == "latest":
            return "v0.20.0"
        else:
            return super().get_ref(version)
