from __future__ import annotations

import re
from subprocess import check_output, PIPE, CalledProcessError
from typing import TYPE_CHECKING, List, Optional, Tuple
import logging

from .types import ApplicationMetadata

if TYPE_CHECKING:
    from ..toolkit import Context


logger = logging.getLogger(__name__)


def get_project_repo(name: str) -> Optional[str]:
    # TODO improve image name and project source directory association
    if name == "xud":
        return "/xud"
    elif name == "arby":
        return "/arby"
    elif name == "boltz":
        return "/go/src/github.com/BoltzExchange/boltz-lnd"
    elif name == "connext":
        return "/connext"
    return None


def get_git_revision_branch(project_repo: str, builder_tag: str) -> Tuple[str, str]:
    cmd = f"docker run -i --rm --workdir {project_repo} --entrypoint git {builder_tag} show HEAD --format='%H%n%D'"
    output = check_output(cmd, shell=True, stderr=PIPE)
    output = output.decode().strip()
    lines = output.splitlines()
    revision = lines[0]
    refs = lines[1].split(", ")
    branch = [ref for ref in refs if ref.startswith("origin/") and "HEAD" not in ref][0]
    branch = branch.replace("origin/", "")
    return revision, branch


def tag_builder_stage(build_tag: str, build_dir:str, build_args: List[str]) -> str:
    builder_tag = build_tag + "__builder"
    args = []
    for arg in build_args:
        if arg.startswith("-t"):
            args.append("-t " + builder_tag)
        else:
            args.append(arg)
    args.append("--target builder")
    check_output("docker build {} {}".format(" ".join(args), build_dir), shell=True, stderr=PIPE)
    return builder_tag


def get_metadata(context: Context, name: str, build_tag: str, build_dir: str, build_args: List[str]) -> ApplicationMetadata:
    try:
        project_repo = get_project_repo(name)
        if not project_repo:
            return ApplicationMetadata(branch=None, revision=None)

        builder_tag = tag_builder_stage(build_tag, build_dir, build_args)

        revision, branch = get_git_revision_branch(project_repo, builder_tag)

        return ApplicationMetadata(branch=branch, revision=revision)
    except CalledProcessError as e:
        print(e.cmd)
        print(e.stdout)
        print(e.stderr)
        raise RuntimeError("Failed to get application metadata for " + name) from e
