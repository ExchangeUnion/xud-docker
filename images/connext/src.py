from tools.core import src


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__("https://github.com/connext/rest-api-client")

    def get_ref(self, version):
        if version == "latest":
            return "5794f5b8c99015074085fbc9859602d7c3f42726"
        elif version == "7.0.0":
            return "5127ad848c3f598a9f23c51dc6d491753740832d"
        elif version == "7.1.0":
            return "26c521ac62181c1d1945a3e252351e24beee8096"
        elif version == "7.1.1":
            return "16fa7aecc19f44dab12e14b9264df63fccb25585"
        elif version == "7.1.2":
            return "5794f5b8c99015074085fbc9859602d7c3f42726"
