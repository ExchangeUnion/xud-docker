from tools.core import src


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__("https://github.com/ethereum/go-ethereum")

    def get_ref(self, version):
        if version == "latest":
            return "v1.9.20"
        else:
            return super().get_ref(version)
