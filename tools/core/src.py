from subprocess import check_output, CalledProcessError, PIPE, STDOUT
import os
import shutil
import logging


class SourceManager:
    def __init__(self, repo_url):
        self.repo_url = repo_url
        self.src_dir = os.path.abspath(".src")
        self.logger = logging.getLogger("core.SourceManager")

    def check(self, repo_url, repo_dir):
        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            return False
        wd = os.getcwd()
        try:
            os.chdir(repo_dir)
            try:
                self._execute(f"git status")
            except CalledProcessError:
                return False

            return self._get_origin_url() == repo_url
        finally:
            os.chdir(wd)

    def _get_origin_url(self):
        cmd = f"git remote get-url origin"
        output = check_output(cmd, shell=True, stderr=PIPE)
        output = output.decode()
        self.logger.debug("$ %s\n%s", cmd, output)
        return output.strip()

    def _clone_repo(self, repo_url, repo_dir):
        self._execute(f"git clone {repo_url} {repo_dir}")

    def ensure_repo(self, repo_url, repo_dir):
        if not self.check(repo_url, repo_dir):
            if os.path.exists(repo_dir):
                shutil.rmtree(repo_dir)

        if not os.path.exists(repo_dir):
            self._clone_repo(repo_url, repo_dir)

    def ensure(self, version):
        repo_dir = self.src_dir
        self.ensure_repo(self.repo_url, repo_dir)
        self.checkout(repo_dir, version)

    def get_ref(self, version):
        if version == "latest":
            return "master"
        else:
            return "v" + version

    def get_dockerfile(self, version):
        return "Dockerfile"

    def get_build_args(self, version):
        return {}

    def _execute(self, cmd):
        output = check_output(cmd, shell=True, stderr=STDOUT)
        self.logger.debug("$ %s\n%s", cmd, output.decode())

    def checkout_repo(self, repo_dir, ref):
        wd = os.getcwd()
        try:
            os.chdir(repo_dir)
            self._execute(f"git fetch")
            self._execute(f"git checkout {ref}")
            self._execute(f"git pull origin {ref}")
            self._execute(f"git clean -xfd")
        finally:
            os.chdir(wd)

    def checkout(self, repo_dir, version):
        ref = self.get_ref(version)
        self.checkout_repo(repo_dir, ref)

    def get_revision(self, repo_dir):
        wd = os.getcwd()
        try:
            os.chdir(repo_dir)
            output = check_output(f"git rev-parse HEAD", shell=True)
            return output.decode().strip()
        finally:
            os.chdir(wd)

    def get_application_revision(self, version):
        return self.get_revision(self.src_dir)
