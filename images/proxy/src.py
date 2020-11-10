from tools.core import src
import os


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__(None)
        self.frontend_dir = os.path.join(self.src_dir, "frontend")
        self.backend_dir = os.path.join(self.src_dir, "backend")

    def ensure(self, version):
        self.ensure_repo("https://github.com/ExchangeUnion/xud-ui-dashboard", self.frontend_dir)
        self.ensure_repo("https://github.com/ExchangeUnion/xud-docker-api", self.backend_dir)
        if version == "latest":
            # change "master" or "main" to a another xud branch for testing
            self.checkout_repo(self.frontend_dir, "feat/initial-sync")
            self.checkout_repo(self.backend_dir, "master")
        else:
            self.checkout_repo(self.frontend_dir, "v" + version)
            self.checkout_repo(self.backend_dir, "v" + version)

    def get_application_revision(self, version):
        r1 = self.get_revision(self.frontend_dir)
        r2 = self.get_revision(self.backend_dir)
        return f"frontend:{r1},backend:{r2}"

