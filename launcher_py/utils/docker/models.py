from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List


@dataclass
class Token:
    repo: str
    value: str
    expired_at: datetime


@dataclass
class Layer:
    digest: str
    size: int


@dataclass
class Image:
    repo: str
    tag: Optional[str]
    digest: str
    created_at: datetime
    labels: Dict[str, str]
    layers: List[Layer]

    @property
    def name(self) -> str:
        if self.tag:
            return f"{self.repo}:{self.tag}"
        else:
            return f"{self.repo}@{self.digest}"
