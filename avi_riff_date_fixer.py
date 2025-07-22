#!/usr/bin/env python3
"""
RIFF-Preserving AVI Date Fixer
Directly modifies date bytes in existing IDIT chunks without corrupting Windows-compatible structure
"""

import struct
import sys
from datetime import datetime, timedelta
from pathlib import Path


def find_idit_chunk(data):
    """Find IDIT chunk in AVI RIFF data."""
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


def parse_canon_date(date_str):
    """Parse Canon date format: 'MON AUG 28 14:14:28 2006'"""
    try:
        # Remove null bytes and extra whitespace
        clean_date = date_str.strip().rstrip("\x00").strip()

        # Parse the date format used by Canon
        dt = datetime.strptime(clean_date, "%a %b %d %H:%M:%S %Y")
        return dt
    except ValueError as e:
        print(f"   ❌ Could not parse date '{clean_date}': {e}")
        return None


def format_canon_date(dt):
    """Format date in Canon format: 'MON AUG 28 14:14:28 2006'"""
    return dt.strftime("%a %b %d %H:%M:%S %Y").upper()


def fix_avi_date_inplace(file_path, time_delta):
    """Fix AVI date by directly modifying IDIT chunk bytes."""
    file_path = Path(file_path)

    print(f"🔧 RIFF-PRESERVING AVI DATE FIXER")
    print(f"📁 File: {file_path}")
    print(f"⏰ Time adjustment: {time_delta}")
    print("=" * 60)

    # Create backup
    backup_path = file_path.with_suffix(".backup" + file_path.suffix)
    try:
        import shutil

        shutil.copy2(file_path, backup_path)
        print(f"💾 Backup created: {backup_path}")
    except Exception as e:
        print(f"❌ Could not create backup: {e}")
        return False

    try:
        # Read the entire file
        with open(file_path, "rb") as f:
            data = bytearray(f.read())

        print(f"📊 File size: {len(data):,} bytes")

        # Find IDIT chunk
        idit_pos, date_data = find_idit_chunk(data)

        if idit_pos is None:
            print("❌ No IDIT chunk found in file")
            # Clean up backup before returning
            if backup_path.exists():
                backup_path.unlink()
            return False

        print(f"🔍 Found IDIT chunk at offset {idit_pos}")

        # Parse current date
        current_date_str = date_data.decode("ascii", errors="ignore")
        print(f"📅 Current date string: '{current_date_str.strip()}'")

        current_date = parse_canon_date(current_date_str)
        if current_date is None:
            print("❌ Could not parse current date")
            return False

        print(f"📅 Parsed current date: {current_date}")

        # Calculate new date
        new_date = current_date + time_delta
        new_date_str = format_canon_date(new_date)
        print(f"📅 New date: {new_date}")
        print(f"📅 New date string: '{new_date_str}'")

        # Prepare new date data (preserve original chunk size)
        original_size = len(date_data)
        new_date_bytes = new_date_str.encode("ascii")

        # Pad or truncate to match original size
        if len(new_date_bytes) < original_size:
            # Pad with null bytes
            new_date_bytes += b"\x00" * (original_size - len(new_date_bytes))
        elif len(new_date_bytes) > original_size:
            # Truncate (shouldn't happen with same format)
            new_date_bytes = new_date_bytes[:original_size]

        print(f"📦 Original chunk size: {original_size} bytes")
        print(f"📦 New data size: {len(new_date_bytes)} bytes")

        # Replace the date data in the file
        date_start = idit_pos + 8
        date_end = date_start + original_size

        data[date_start:date_end] = new_date_bytes

        # Write the modified data back
        with open(file_path, "wb") as f:
            f.write(data)

        print("✅ IDIT chunk successfully modified")
        print("🔧 RIFF structure preserved")

        # Clean up backup if successful
        backup_path.unlink()
        print("🗑️ Backup removed")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")

        # Restore from backup
        try:
            import shutil

            shutil.copy2(backup_path, file_path)
            backup_path.unlink()
            print("🔄 File restored from backup")
        except Exception as restore_error:
            print(f"❌ Could not restore from backup: {restore_error}")

        return False


def main():
    """Main function for command-line usage."""
    if len(sys.argv) != 3:
        print("Usage: python avi_riff_date_fixer.py <avi_file> <time_adjustment>")
        print("Examples:")
        print("  python avi_riff_date_fixer.py video.avi +1d")
        print("  python avi_riff_date_fixer.py video.avi -2h")
        print("  python avi_riff_date_fixer.py video.avi +1y 2m 3d")
        sys.exit(1)

    avi_file = sys.argv[1]
    time_str = sys.argv[2]

    if not Path(avi_file).exists():
        print(f"Error: File not found: {avi_file}")
        sys.exit(1)

    # Parse time adjustment (simple version)
    try:
        if time_str.startswith("+"):
            time_str = time_str[1:]
            multiplier = 1
        elif time_str.startswith("-"):
            time_str = time_str[1:]
            multiplier = -1
        else:
            multiplier = 1

        if time_str.endswith("d"):
            days = int(time_str[:-1])
            time_delta = timedelta(days=days * multiplier)
        elif time_str.endswith("h"):
            hours = int(time_str[:-1])
            time_delta = timedelta(hours=hours * multiplier)
        elif time_str.endswith("m"):
            minutes = int(time_str[:-1])
            time_delta = timedelta(minutes=minutes * multiplier)
        else:
            # Assume days
            days = int(time_str)
            time_delta = timedelta(days=days * multiplier)

    except ValueError:
        print(f"Error: Invalid time format: {time_str}")
        sys.exit(1)

    success = fix_avi_date_inplace(avi_file, time_delta)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
