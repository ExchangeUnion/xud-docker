from dataclasses import dataclass
from datetime import datetime


@dataclass
class ImageMetadata:
    repo: str
    tag: str
    digest: str
    revision: str
    application_revision: str
    created_at: datetime
