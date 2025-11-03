"""Simple datetime utilities."""
import datetime
from datetime import datetime as dt


def format_now(simple_date: str = "%Y-%m-%d") -> dict[str, str]:
    """Format current date and time.
    
    Returns:
        Dictionary with 'now_date', 'now_time', and 'simple_date' keys
    """
    now = dt.now(datetime.timezone.utc)
    return {
        "now_date": now.strftime("%Y-%m-%d"),
        "now_time": now.strftime("%H:%M:%S"),
        "simple_date": now.strftime(simple_date),
    }

