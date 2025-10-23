"""
Date utilities - centralized date parsing logic
Used across multiple endpoints to avoid duplication
"""
import pandas as pd
from config import SUPPORTED_DATE_FORMATS


def parse_date_flexible(date_str):
    """
    Parse date string supporting multiple formats
    Handles: YYYY-MM-DD, DD-Month-YYYY, and pandas auto-parsing

    Args:
        date_str: Date string to parse

    Returns:
        pd.Timestamp or None if parsing fails

    Examples:
        >>> parse_date_flexible('2025-10-24')
        Timestamp('2025-10-24 00:00:00')

        >>> parse_date_flexible('24-October-2025')
        Timestamp('2025-10-24 00:00:00')

        >>> parse_date_flexible(None)
        None
    """
    if pd.isna(date_str):
        return None

    date_str = str(date_str).strip()

    # Handle special case
    if date_str in ['Data Belum Ada', 'nan', '']:
        return None

    # Try supported formats first
    for fmt in SUPPORTED_DATE_FORMATS:
        try:
            return pd.to_datetime(date_str, format=fmt)
        except (ValueError, TypeError):
            continue

    # Fallback to pandas auto-parsing
    try:
        return pd.to_datetime(date_str)
    except (ValueError, TypeError):
        return None


def get_days_since(target_date, from_date=None):
    """
    Calculate days between two dates

    Args:
        target_date: pd.Timestamp - the date to measure from
        from_date: pd.Timestamp - the reference date (default: today)

    Returns:
        int - number of days, or 0 if target_date is None
    """
    if pd.isna(target_date):
        return 0

    if from_date is None:
        from_date = pd.Timestamp.now()

    delta = from_date - target_date
    return int(delta.days)


def get_tenure_days(registration_date, to_date=None):
    """
    Calculate tenure in days from registration date

    Args:
        registration_date: pd.Timestamp - customer registration date
        to_date: pd.Timestamp - reference date (default: today)

    Returns:
        int - number of days since registration
    """
    return get_days_since(registration_date, to_date)
