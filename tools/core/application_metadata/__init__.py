from __future__ import annotations
from typing import TYPE_CHECKING
from .xud import get_metadata as get_xud_metadata
from .types import ApplicationMetadata

if TYPE_CHECKING:
    from ..toolkit import Context


def get_application_metadata(name: str, build_tag: str, context: Context) -> ApplicationMetadata:
    if name == "xud":
        return get_xud_metadata(build_tag, context)
    else:
        return ApplicationMetadata(branch=None, revision=None)
