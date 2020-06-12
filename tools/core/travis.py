from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .toolkit import Context


class TravisClient:
    pass


class TravisTemplate:
    def __init__(self, context: Context):
        self.context = context
