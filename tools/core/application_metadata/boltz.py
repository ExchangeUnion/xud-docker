from __future__ import annotations

import re
from subprocess import check_output, PIPE, CalledProcessError
from typing import TYPE_CHECKING, List
import logging

from .types import ApplicationMetadata

if TYPE_CHECKING:
    from ..toolkit import Context


logger = logging.getLogger(__name__)


def get_metadata(context: Context, build_tag: str, build_dir: str, build_args: List[str]) -> ApplicationMetadata:
    builder_tag = build_tag + "__builder"
    args = []
    for arg in build_args:
        if arg.startswith("-t"):
            args.append("-t " + builder_tag)
        else:
            args.append(arg)
    args.append("--target builder")
    try:
        check_output("docker build {} {}".format(" ".join(args), build_dir), shell=True, stderr=PIPE)
    except CalledProcessError as e:
        logger.exception("Failed to tag builder stage image as %s: %r", builder_tag, e.stderr)
        raise

    project_src = "/go/src/github.com/BoltzExchange/boltz-lnd"

    try:
        output = check_output(f"docker run -i --rm --entrypoint cat {builder_tag} {project_src}/.git/HEAD", shell=True, stderr=PIPE)
    except CalledProcessError as e:
        logger.exception("Failed to get Git HEAD in image %s: %r", builder_tag, e.stderr)
        raise

    output = output.decode().strip()
    p = re.compile("^ref: (refs/heads/(.+))$")
    m = p.match(output)
    assert m
    ref = m.group(1)
    branch = m.group(2)

    try:
        output = check_output(f"docker run -i --rm --entrypoint cat {builder_tag} {project_src}/.git/{ref}", shell=True, stderr=PIPE)
    except CalledProcessError as e:
        logger.exception("Failed to get Git reference %s in image %s: %r", ref, builder_tag, e.stderr)
    output = output.decode().strip()
    revision = output

    assert branch
    assert revision

    return ApplicationMetadata(branch=branch, revision=revision)
