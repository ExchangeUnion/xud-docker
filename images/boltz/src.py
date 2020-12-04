from tools.core import src


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__("https://github.com/BoltzExchange/boltz-lnd")

    def get_build_args(self, version):
        revision = self.get_revision(self.src_dir)
        print(revision[:7])
        return {
            "GIT_REVISION": revision[:7]
        }

    def get_ref(self, version):
        if version == "latest":
            return "master"
        else:
            return "v" + version
