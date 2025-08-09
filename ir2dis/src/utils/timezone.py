#!/usr/bin/env python3
"""
Utility functions for timezone handling.
"""

from datetime import datetime
import pytz

def format_timestamp(timestamp: datetime, timezone_str: str) -> str:
    """
    Format a timestamp in the specified timezone.
    
    Args:
        timestamp (datetime): The timestamp to format
        timezone_str (str): Timezone string (e.g., 'Europe/Berlin')
        
    Returns:
        str: Formatted timestamp string
    """
    try:
        # Convert to the specified timezone
        tz = pytz.timezone(timezone_str)
        localized_timestamp = timestamp.replace(tzinfo=pytz.UTC).astimezone(tz)
        return localized_timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')
    except Exception:
        # Fallback to UTC if timezone conversion fails
        return timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')

def get_timezone_offset(timezone_str: str) -> int:
    """
    Get the timezone offset in hours.
    
    Args:
        timezone_str (str): Timezone string
        
    Returns:
        int: Timezone offset in hours
    """
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        return now.utcoffset().total_seconds() / 3600
    except Exception:
        # Default to UTC
        return 0
