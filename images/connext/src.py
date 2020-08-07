from tools.core import src


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__("https://github.com/connext/rest-api-client")

    def get_ref(self, version):
        if version == "latest":
            # connext commit lock
            return "5127ad848c3f598a9f23c51dc6d491753740832d"
        elif version == "7.0.0":
            return "5127ad848c3f598a9f23c51dc6d491753740832d"
