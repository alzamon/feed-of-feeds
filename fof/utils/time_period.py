import re
from datetime import timedelta

def parse_time_period(period_str: str) -> timedelta:
    """
    Parse a string like '7d', '12h', '30m', '10s' into a timedelta.
    Supports days (d), hours (h), minutes (m), seconds (s).
    """
    if not isinstance(period_str, str):
        raise ValueError("Time period must be a string")
    pattern = r'(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?'
    match = re.fullmatch(pattern, period_str.strip())
    if not match:
        raise ValueError(f"Invalid time period string: {period_str}")
    days, hours, minutes, seconds = match.groups(default='0')
    return timedelta(
        days=int(days),
        hours=int(hours),
        minutes=int(minutes),
        seconds=int(seconds),
    )

def timedelta_to_period_str(td: timedelta) -> str:
    """
    Serialize a timedelta to a compact period string like '7d12h30m10s'.
    """
    seconds = int(td.total_seconds())
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    result = ''
    if days: result += f'{days}d'
    if hours: result += f'{hours}h'
    if minutes: result += f'{minutes}m'
    if seconds or not result: result += f'{seconds}s'
    return result
