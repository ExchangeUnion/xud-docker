from __future__ import annotations

import re
from subprocess import check_output, PIPE
from typing import TYPE_CHECKING, List

from .types import ApplicationMetadata

if TYPE_CHECKING:
    from ..toolkit import Context


def get_metadata(context: Context, build_tag: str, build_dir: str, build_args: List[str]) -> ApplicationMetadata:
    ref = None
    branch = None
    revision = None

    try:
        output = check_output(f"docker run -i --rm --entrypoint cat {build_tag} /app/.git/HEAD", shell=True,
                              stderr=PIPE)
        output = output.decode().strip()
        p = re.compile("^ref: (refs/heads/(.+))$")
        m = p.match(output)
        assert m
        ref = m.group(1)
        branch = m.group(2)
    except Exception:
        pass

    if not revision:
        try:
            output = check_output(f"docker run -i --rm --entrypoint cat {build_tag} /app/.git/{ref}", shell=True,
                                  stderr=PIPE)
            output = output.decode().strip()
            revision = output
        except Exception as e:
            raise RuntimeError(e, "Failed to get application revision from {}".format(build_tag))

    return ApplicationMetadata(branch=branch, revision=revision)
