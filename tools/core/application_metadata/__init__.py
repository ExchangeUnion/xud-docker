from __future__ import annotations
from typing import TYPE_CHECKING, List
from .common import get_metadata
from .types import ApplicationMetadata

if TYPE_CHECKING:
    from ..toolkit import Context


def get_application_metadata(context: Context, name: str, build_tag: str, build_dir: str, args: List[str]) -> ApplicationMetadata:
    return get_metadata(context, name, build_tag, build_dir, args)
