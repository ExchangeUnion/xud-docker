from __future__ import annotations

import json
from typing import Optional, TYPE_CHECKING, Dict, List
from urllib.request import urlopen
import re

if TYPE_CHECKING:
    from .toolkit import Context


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

    def get_revision(self, name, branch):
        if name == "xud":
            repo = "ExchangeUnion/xud"
        else:
            return None

        try:
            tag = self.get_tag(repo, branch)
            if tag:
                return tag
            else:
                return self.get_branch_revision(repo, branch)
        except:
            return None

    def get_commit(self, ref: str) -> Dict:
        r = urlopen(f"https://api.github.com/repos/ExchangeUnion/xud/commits/{ref}")
        return json.loads(r.read().decode())

    def get_branches(self, commit: str) -> List[str]:
        # try to get branches which contain the commit using GitHub undocumented API
        r = urlopen(f"https://github.com/ExchangeUnion/xud/branch_commits/{commit}")
        branches = []
        p = re.compile(r"^.*\"branch\".*>([^<]+)<.*$")
        for line in r.read().decode().splitlines():
            m = p.match(line)
            if m:
                branches.append(m.group(1))
        return branches


class GithubTemplate:
    def __init__(self, context: Context):
        self.context = context
        self._client = GithubClient()

    def get_branch_head_revision(self, name: str, branch: str) -> Optional[str]:
        return self._client.get_revision(name, branch)

    def expand_short_sha(self, sha: str) -> str:
        return self._client.get_commit(sha)["sha"]

    def get_branches(self, commit: str) -> List[str]:
        return self._client.get_branches(commit)
