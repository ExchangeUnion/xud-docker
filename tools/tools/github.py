from urllib.request import urlopen
import json


class GithubClient:
    def get_tag(self, repo, tag):
        try:
            r = urlopen(f"https://api.github.com/repos/{repo}/tags")
            target = [t for t in json.loads(r.read().decode()) if t["name"] == tag]
            if len(target) == 0:
                return None
            else:
                return target[0]["commit"]["sha"]
        except Exception as e:
            raise RuntimeError(e, "Failed to get GitHub repository {} tag {}".format(repo, tag))

    def get_branch_revision(self, repo, branch):
        try:
            r = urlopen(f"https://api.github.com/repos/{repo}/git/refs/heads/{branch}")
            return json.loads(r.read().decode())["object"]["sha"]
        except Exception as e:
            raise RuntimeError(e, "Failed to get GitHub repository {} branch {} revision".format(repo, branch))

    def get_revision(self, repo, branch):
        try:
            tag = self.get_tag(repo, branch)
            if tag:
                return tag
            else:
                return self.get_branch_revision(repo, branch)
        except:
            return None
