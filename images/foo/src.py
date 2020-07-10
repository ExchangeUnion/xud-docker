from tools.core import src


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__(None)

    def ensure(self, version):
        pass

    def get_revision(self, repo_dir):
        return "<empty>"
