from __future__ import annotations
from typing import TYPE_CHECKING, List
from .xud import get_metadata as get_xud_metadata
from .arby import get_metadata as get_arby_metadata
from .boltz import get_metadata as get_boltz_metadata
from .types import ApplicationMetadata

if TYPE_CHECKING:
    from ..toolkit import Context


def get_application_metadata(context: Context, name: str, build_tag: str, build_dir: str, build_args: List[str]) -> ApplicationMetadata:
    if name == "xud":
        return get_xud_metadata(context, build_tag, build_dir, build_args)
    elif name == "arby":
        return get_arby_metadata(context, build_tag, build_dir, build_args)
    elif name == "boltz":
        return get_boltz_metadata(context, build_tag, build_dir, build_args)
    else:
        return ApplicationMetadata(branch=None, revision=None)
