from __future__ import annotations

import re
from subprocess import check_output, PIPE, CalledProcessError
from typing import TYPE_CHECKING, List, Optional
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


def get_git_branch(project_repo: str, builder_tag: str) -> Optional[str]:
    cmd = f"docker run -i --rm --workdir {project_repo} --entrypoint git {builder_tag} rev-parse --abbrev-ref HEAD"
    output = check_output(cmd, shell=True, stderr=PIPE)
    output = output.decode().strip()
    if output == "HEAD":
        return None
    return output


def get_git_revision(project_repo: str, builder_tag: str) -> str:
    cmd = f"docker run -i --rm --workdir {project_repo} --entrypoint git {builder_tag} rev-parse HEAD"
    output = check_output(cmd, shell=True, stderr=PIPE)
    output = output.decode().strip()
    return output


def get_git_branch_2(project_repo: str, builder_tag: str) -> str:
    cmd = f"docker run -i --rm --entrypoint cat {builder_tag} {project_repo}/.git/FETCH_HEAD"
    try:
        output = check_output(cmd, shell=True, stderr=PIPE)
    except CalledProcessError as e:
        logger.exception("Failed to get Git FETCH_HEAD in image %s: %r", builder_tag, e.stderr)
        raise

    output = output.decode().strip()
    # output like
    # 22a3f5135263ab3532b9089de0c4ce910c77b8d3		branch 'master' of https://github.com/ExchangeUnion/market-maker-tools
    p = re.compile("^(.+)\s+branch '(.+)' of (.+)$")
    m = p.match(output)
    assert m, "Regex pattern mismatched. cmd=%r, output=%r, pattern=%r" % (cmd, output, p)
    revision = m.group(1)
    branch = m.group(2)
    repo_url = m.group(3)
    return branch


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
    project_repo = get_project_repo(name)
    if not project_repo:
        return ApplicationMetadata(branch=None, revision=None)

    builder_tag = tag_builder_stage(build_tag, build_dir, build_args)

    revision = get_git_revision(project_repo, builder_tag)
    branch = get_git_branch(project_repo, builder_tag)
    if not branch:
        branch = get_git_branch_2(project_repo, builder_tag)

    return ApplicationMetadata(branch=branch, revision=revision)
