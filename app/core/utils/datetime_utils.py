from datetime import datetime, timezone
from typing import Optional

def get_utc_now() -> datetime:
    """Get current UTC time with timezone info.
    
    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)

def format_utc_datetime(dt: Optional[datetime] = None) -> str:
    """Format a datetime to ISO format with timezone info.
    
    Args:
        dt: Datetime to format. If None, uses current UTC time.
        
    Returns:
        str: ISO formatted datetime string with timezone info
    """
    if dt is None:
        dt = get_utc_now()
    return dt.isoformat()
