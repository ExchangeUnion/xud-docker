from datetime import datetime, timezone
import re
from launcher.errors import ParseError


DOCKER_DATETIME_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}).(\d+)Z$")


def parse_datetime(dt_str: str) -> datetime:
    """
    # 2020-12-29T20:11:12.0115313Z
    """
    m = DOCKER_DATETIME_PATTERN.match(dt_str)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        hour = int(m.group(4))
        minute = int(m.group(5))
        second = int(m.group(6))
        microsecond = int(m.group(7)[:6])
        return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=timezone.utc)
    else:
        raise ParseError(dt_str)
