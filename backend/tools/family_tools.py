from datetime import UTC, datetime

from strands import tool


@tool
def get_current_datetime() -> str:
    """Return the current UTC date and time for deadline and schedule reasoning."""
    return datetime.now(UTC).isoformat()
