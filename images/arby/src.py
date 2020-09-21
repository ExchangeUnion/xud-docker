from tools.core import src


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__("https://github.com/ExchangeUnion/market-maker-tools")

    def get_build_args(self, version):
        revision = self.get_revision(self.src_dir)
        return {
            "GIT_REVISION": revision[:8]
        }

    def get_ref(self, version):
        if version == "latest":
            # change "master" to a another xud branch for testing
            return "feat/config-hardening"
        else:
            return "v" + version
