from subprocess import check_output, CalledProcessError, PIPE
import os
import shutil


class SourceManager:
    def __init__(self, repo_url):
        self.repo_url = repo_url
        self.src_dir = os.path.abspath(".src")

    def check(self, repo_url):
        try:
            check_output(f"git status", shell=True)
        except CalledProcessError:
            return False

        output = check_output(f"git remote get-url origin", shell=True)
        output = output.decode().strip()
        return output == repo_url

    def ensure_repo(self, repo_url, repo_dir):
        print("Ensure Git repository {} ({})".format(self.src_dir, self.repo_url))
        wd = os.getcwd()
        try:
            if os.path.exists(repo_dir):
                os.chdir(repo_dir)
                if not self.check(repo_url):
                    os.chdir(wd)
                    shutil.rmtree(repo_dir)
            else:
                print(repo_dir, "is not existed")

            if not os.path.exists(repo_dir):
                check_output(f"git clone {repo_url} {repo_dir}", shell=True)
        finally:
            os.chdir(wd)

    def ensure(self, version):
        self.ensure_repo(self.repo_url, self.src_dir)
        self.checkout(self.src_dir, version)

    def get_ref(self, version):
        if version == "latest":
            return "master"
        else:
            return "v" + version

    def get_dockerfile(self, version):
        return "Dockerfile"

    def get_build_args(self, version):
        return {}

    def checkout_repo(self, repo_dir, ref):
        wd = os.getcwd()
        try:
            os.chdir(repo_dir)

            print("$ git fetch")
            output = check_output(f"git fetch", shell=True)
            print(output.decode(), end="", flush=True)

            print("$ git checkout " + ref)
            output = check_output(f"git checkout {ref}", shell=True)
            print(output.decode(), end="", flush=True)

            print("$ git pull origin " + ref)
            output = check_output(f"git pull origin {ref}", shell=True)
            print(output.decode(), end="", flush=True)

            print("$ git clean -xfd")
            output = check_output(f"git clean -xfd", shell=True)
            print(output.decode(), end="", flush=True)

            # FIXME handle rebased case

        finally:
            os.chdir(wd)

    def checkout(self, repo_dir, version):
        ref = self.get_ref(version)
        print("Checkout version {}({}) on {}".format(version, ref, repo_dir))
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
