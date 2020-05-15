import os
from subprocess import check_output, CalledProcessError, PIPE
import sys

from .errors import FatalError


class GitInfo:
    def __init__(self, project_dir, commit_before_travis):
        cwd = os.getcwd()

        self.branch = None
        self.revision = None
        self.master_head = None
        self.history = None
        self.git_repo = False

        try:
            os.chdir(project_dir)

            if not os.path.exists(".git"):
                return

            b = os.popen("git rev-parse --abbrev-ref HEAD").read().strip()
            if b == "HEAD":
                b = os.environ["TRAVIS_BRANCH"]
            if b == "local":
                raise FatalError("Git branch name (local) is reserved")
            if "__" in b:
                raise FatalError("Git branch name (%s) contains \"__\"" % b)
            r = os.popen("git rev-parse HEAD").read().strip()
            if os.system("git diff --quiet") != 0:
                r = r + "-dirty"
            master = self.get_master_commit_hash()
            branch = b
            if branch == "master":
                history = self.get_branch_history(commit_before_travis)
            else:
                history = self.get_branch_history(master)

            output = check_output("git diff --name-only", shell=True)
            output = output.decode().strip()
            if len(output) > 0:
                history.insert(0, "HEAD")

            self.branch = b
            self.revision = r
            self.master_head = master
            self.history = history

        finally:
            os.chdir(cwd)

    @property
    def tag_safe_branch(self):
        return self.branch.replace("/", "-")

    def get_master_commit_hash(self):
        try:
            return check_output("git rev-parse master", shell=True, stderr=PIPE).decode().splitlines()[0]
        except CalledProcessError:
            # <hash> refs/heads/master
            return check_output("git ls-remote origin master", shell=True, stderr=PIPE).decode().split()[0]

    def get_branch_history(self, master):
        cmd = "git log --oneline --pretty=format:%h --abbrev=-1 {}..".format(master[:7])
        return check_output(cmd, shell=True, stderr=PIPE).decode().splitlines()

    def get_commit_message(self, commit):
        if commit == "HEAD":
            return ""
        cmd = "git show -s --format=%B {}".format(commit)
        return check_output(cmd, shell=True, stderr=PIPE).decode().splitlines()[0]