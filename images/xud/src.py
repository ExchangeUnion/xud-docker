from tools.core import src


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__("https://github.com/ExchangeUnion/xud")

    def get_build_args(self, version):
        revision = self.get_revision(self.src_dir)
        return {
            "GIT_REVISION": revision[:8]
        }

    def get_ref(self, version):
        if version == "latest":
            # you could change "master" to a custom branch when testing some xud feature locally
            return "master"
        else:
            return "v" + version
