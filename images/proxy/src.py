from tools.core import src


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__("https://github.com/ExchangeUnion/xud-docker-api-poc")

    def get_ref(self, version):
        if version == "latest":
            # change "master" to a another xud branch for testing
            return "master"
        else:
            return "v" + version
