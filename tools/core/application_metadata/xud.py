from __future__ import annotations

import re
from subprocess import check_output, PIPE
from typing import TYPE_CHECKING

from .types import ApplicationMetadata

if TYPE_CHECKING:
    from ..toolkit import Context


def get_metadata(build_tag: str, context: Context) -> ApplicationMetadata:
    ref = None
    branch = None
    revision = None

    try:
        output = check_output(f"docker run -i --rm --entrypoint cat {build_tag} /app/.git/HEAD", shell=True,
                              stderr=PIPE)
        output = output.decode().strip()
        p = re.compile("^ref: (refs/heads/(.+))$")
        m = p.match(output)
        if m:
            ref = m.group(1)
            branch = m.group(2)
    except Exception:
        pass

    if not ref:
        try:
            output = check_output(
                f"docker run -i --rm --entrypoint cat {build_tag} /app/dist/Version.js | grep exports.default",
                shell=True, stderr=PIPE)
            # exports.default = '-c46bc2f';
            output = output.decode().strip()
            p = re.compile(r"^exports\.default = '-(.+)';")
            m = p.match(output)
            if m:
                revision = m.group(1)
        except Exception as e:
            raise RuntimeError(e, "Failed to get application branch from {}".format(build_tag))

    if not revision:
        try:
            output = check_output(f"docker run -i --rm --entrypoint cat {build_tag} /app/.git/{ref}", shell=True,
                                  stderr=PIPE)
            output = output.decode().strip()
            revision = output
        except Exception as e:
            raise RuntimeError(e, "Failed to get application revision from {}".format(build_tag))

    if len(revision) == 7:
        revision = context.github_template.expand_short_sha(revision)
        branch = ",".join(context.github_template.get_branches(revision))

    return ApplicationMetadata(branch=branch, revision=revision)
