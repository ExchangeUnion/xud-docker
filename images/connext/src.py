from tools.core import src


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__("https://github.com/connext/rest-api-client")

    def get_ref(self, version):
        if version == "latest":
            return "master"
        elif version == "7.0.0-alpha.14":
            return "fe1876a0411e0b9928825ae51104e16a9fd7b787"
