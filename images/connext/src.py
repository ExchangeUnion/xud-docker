from tools.core import src


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__("https://github.com/connext/rest-api-client")

    def get_ref(self, version):
        if version == "latest":
            # connext commit lock
            return "08a453eac82b4c01ff9e85a7780b2ab89c7e9081"
        elif version == "7.0.0":
            return "08a453eac82b4c01ff9e85a7780b2ab89c7e9081"
