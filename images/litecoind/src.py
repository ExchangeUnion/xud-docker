from tools.core import src


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__("https://github.com/litecoin-project/litecoin")

    def get_ref(self, version):
        if version == "latest":
            return "v0.18.1"
        else:
            return super().get_ref(version)
