import time
import re

zone_matcher = re.compile(".*([\\-\\+])(\\d\\d):(\\d\\d)$")
date_time_matcher = re.compile(
    "^(\\d\\d\\d\\d)-(\\d\\d)-(\\d\\d)T(\\d\\d):(\\d\\d):(\\d\\d)(\.\\d+)?"
)


def parse_iso(isostr: str) -> int:
    "Parses ISO8601 datetime and returns UTC seconds since `time` epoch."
    offset_seconds = 0
    offset_match = zone_matcher.match(isostr)
    if offset_match:
        sign = offset_match.group(1)
        offset_hours = int(offset_match.group(2))
        offset_minutes = int(offset_match.group(3))
        offset_seconds = (offset_hours * 60 + offset_minutes) * 60
        if sign == "+":
            offset_seconds = -offset_seconds
    hour = min = sec = 0
    dt_match = date_time_matcher.match(isostr)
    if dt_match:
        year = int(dt_match.group(1))
        month = int(dt_match.group(2))
        day = int(dt_match.group(3))

        hour = int(dt_match.group(4))
        min = int(dt_match.group(5))
        sec = int(dt_match.group(6))

        if any(part is None for part in (year, month, day, hour, min, sec)):
            raise ValueError("invalid datetime")

    epoch_local_time = time.mktime((year, month, day, hour, min, sec, 0, 0))

    epoch_utc_time = epoch_local_time + offset_seconds
    return epoch_utc_time

def timedelta_pformat(td: int, now_threshold: int = 30) -> str:
    assert td > 0, "negative time delta not supported"
    # formatted = "in "
    formatted = ""
    seconds = td

    minutes_total = seconds // 60
    hours = minutes_total // 60
    minutes = minutes_total % 60

    if hours:
        formatted += f"{hours}h"
    if minutes:
        formatted += f"{minutes}m"

    if not hours and not minutes and td > 0:
        if seconds < now_threshold:
            formatted = "now"
        else:
            # now_threshold < td < 60
            # so we can round to 1 min
            formatted += "1m"

    return formatted


def now_epoch() -> int:
    return time.mktime(time.gmtime())


def next_full_minute() -> int:
    """calculate next full minute"""
    (y, m, d, hour, minute, second, _, _) = time.gmtime(now_epoch() + 60)
    second = 0
    return time.mktime((y, m, d, hour, minute, second, 0, 0))