"""
Timezone Utility Module - Consistent DateTime Handling

Provides timezone-aware datetime functions that respect the AUTOMAGIK_TIMEZONE configuration
to ensure consistent timestamps across all workflow operations.
"""

from datetime import datetime
import pytz
from typing import Optional

from automagik.config import settings


def get_current_time() -> datetime:
    """
    Get current time in the configured timezone.
    
    Returns:
        datetime: Current time with timezone info
    """
    tz = pytz.timezone(settings.AUTOMAGIK_TIMEZONE)
    return datetime.now(tz)


def get_utc_time() -> datetime:
    """
    Get current time in UTC.
    
    Returns:
        datetime: Current UTC time (timezone-naive for compatibility)
    """
    return datetime.utcnow()


def convert_to_local(utc_time: datetime) -> datetime:
    """
    Convert UTC time to the configured local timezone.
    
    Args:
        utc_time: UTC datetime (timezone-naive)
        
    Returns:
        datetime: Time converted to local timezone
    """
    tz = pytz.timezone(settings.AUTOMAGIK_TIMEZONE)
    return utc_time.replace(tzinfo=pytz.UTC).astimezone(tz)


def convert_to_utc(local_time: datetime) -> datetime:
    """
    Convert local time to UTC.
    
    Args:
        local_time: Local datetime (timezone-aware or naive)
        
    Returns:
        datetime: Time converted to UTC (timezone-naive for compatibility)
    """
    if local_time.tzinfo is None:
        # Assume it's in the configured timezone
        tz = pytz.timezone(settings.AUTOMAGIK_TIMEZONE)
        local_time = tz.localize(local_time)
    
    return local_time.astimezone(pytz.UTC).replace(tzinfo=None)


def get_timezone_aware_now() -> datetime:
    """
    Get timezone-aware current time that's compatible with database operations.
    
    This function provides a consistent timestamp that accounts for the configured
    timezone while remaining compatible with existing database schema.
    
    Returns:
        datetime: Current time adjusted for timezone but without timezone info
                 (for compatibility with existing timezone-naive database columns)
    """
    if settings.AUTOMAGIK_TIMEZONE == "UTC":
        return datetime.utcnow()
    
    # Get current time in configured timezone
    tz = pytz.timezone(settings.AUTOMAGIK_TIMEZONE)
    local_time = datetime.now(tz)
    
    # Return as timezone-naive for database compatibility
    return local_time.replace(tzinfo=None)


def format_timestamp_for_api(dt: Optional[datetime] = None) -> str:
    """
    Format datetime for API responses with timezone information.
    
    Args:
        dt: Datetime to format (defaults to current time)
        
    Returns:
        str: ISO format timestamp with timezone
    """
    if dt is None:
        dt = get_current_time()
    elif dt.tzinfo is None:
        # Assume it's in the configured timezone
        tz = pytz.timezone(settings.AUTOMAGIK_TIMEZONE)
        dt = tz.localize(dt)
    
    return dt.isoformat()