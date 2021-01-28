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
            self.checkout_repo(self.frontend_dir, "main")
            self.checkout_repo(self.backend_dir, "master")
        elif version == "1.3.0":
            self.checkout_repo(self.frontend_dir, "v1.2.0")
            self.checkout_repo(self.backend_dir, "v1.3.0")
        else:
            self.checkout_repo(self.frontend_dir, "v" + version)
            self.checkout_repo(self.backend_dir, "v" + version)

    def get_application_revision(self, version):
        r1 = self.get_revision(self.frontend_dir)
        r2 = self.get_revision(self.backend_dir)
        return f"frontend:{r1},backend:{r2}"

    def checkout_repo(self, repo_dir, ref):
        if "backend" in repo_dir:
            if "PROXY_BACKEND_REPO" not in os.environ:
                super().checkout_repo(repo_dir, ref)
                return

            src_dir = os.getenv("PROXY_BACKEND_REPO")
            if not src_dir.endswith("/"):
                src_dir = src_dir + "/"

            dest_dir = repo_dir
            if not dest_dir.endswith("/"):
                dest_dir = dest_dir + "/"

            # -a archive mode
            # -v verbose
            # -z compress
            # -h human-readable
            os.system("rsync -avzh --exclude='.git' --exclude='.idea' %s %s" % (src_dir, dest_dir))

        elif "frontend" in repo_dir:
            super().checkout_repo(repo_dir, ref)
