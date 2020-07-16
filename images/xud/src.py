from tools.core import src


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__("https://github.com/ExchangeUnion/xud")

    def get_build_args(self, version):
        revision = self.get_revision(self.src_dir)
        return {
            "GIT_REVISION": revision[:8]
        }
