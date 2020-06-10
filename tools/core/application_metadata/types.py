from __future__ import annotations
from typing import Optional
from dataclasses import dataclass


@dataclass
class ApplicationMetadata:
    branch: Optional[str]
    revision: Optional[str]
