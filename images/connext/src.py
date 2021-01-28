from tools.core import src


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__("https://github.com/connext/rest-api-client")

    def get_ref(self, version):
        if version == "latest":
            return "1.3.6"
        elif version == "1.3.6-1":
            return "1.3.6"
        else:
            return version
