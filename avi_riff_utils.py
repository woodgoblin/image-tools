#!/usr/bin/env python3
"""
AVI RIFF Utilities
Shared functions for AVI RIFF metadata manipulation across different tools.
"""

import struct
from datetime import datetime
from typing import Optional, Tuple


def find_idit_chunk(data: bytearray) -> Tuple[Optional[int], Optional[bytes]]:
    """
    Find IDIT chunk in AVI RIFF data.

    Args:
        data: AVI file data as bytearray

    Returns:
        Tuple of (chunk_position, date_data) or (None, None) if not found
    """
    # Look for IDIT signature
    pos = data.find(b"IDIT")
    if pos == -1:
        return None, None

    # IDIT chunk structure: IDIT + 4-byte size + data
    if pos + 4 >= len(data):
        return None, None

    # Read the chunk size (little-endian)
    size_bytes = data[pos + 4 : pos + 8]
    if len(size_bytes) != 4:
        return None, None

    chunk_size = struct.unpack("<L", size_bytes)[0]

    # Get the actual date data
    date_start = pos + 8
    date_end = date_start + chunk_size

    if date_end > len(data):
        return None, None

    date_data = data[date_start:date_end]

    return (pos, date_data)


def parse_canon_date(date_str: str) -> Optional[datetime]:
    """
    Parse Canon date format: 'MON AUG 28 14:14:28 2006'

    Args:
        date_str: Date string from AVI metadata

    Returns:
        Parsed datetime object or None if parsing fails
    """
    try:
        # Remove null bytes and extra whitespace
        clean_date = date_str.strip().rstrip("\x00").strip()

        # Parse the date format used by Canon
        dt = datetime.strptime(clean_date, "%a %b %d %H:%M:%S %Y")
        return dt
    except ValueError:
        return None


def format_canon_date(dt: datetime) -> str:
    """
    Format date in Canon format: 'MON AUG 28 14:14:28 2006'

    Args:
        dt: Datetime object to format

    Returns:
        Formatted date string in Canon format
    """
    return dt.strftime("%a %b %d %H:%M:%S %Y").upper()
