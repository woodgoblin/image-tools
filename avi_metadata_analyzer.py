#!/usr/bin/env python3
"""
Comprehensive AVI Metadata Analyzer
Shows ALL possible date fields from every source to identify what Windows File Explorer reads
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def analyze_avi_metadata(file_path):
    """Analyze all possible metadata sources for an AVI file."""
    file_path = Path(file_path)

    print(f"🎯 COMPREHENSIVE AVI METADATA ANALYSIS")
    print(f"📁 File: {file_path}")
    print(f"📊 File Size: {file_path.stat().st_size:,} bytes")
    print("=" * 80)

    # 1. FILE SYSTEM TIMESTAMPS
    print("\n📅 1. FILE SYSTEM TIMESTAMPS:")
    try:
        stat = file_path.stat()
        print(f"   📝 Creation Time:     {datetime.fromtimestamp(stat.st_ctime)}")
        print(f"   ✏️  Modification Time: {datetime.fromtimestamp(stat.st_mtime)}")
        print(f"   👁️  Access Time:      {datetime.fromtimestamp(stat.st_atime)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 2. FFPROBE - ALL METADATA
    print("\n🎬 2. FFPROBE - ALL METADATA:")
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(file_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)

            # Format metadata
            if "format" in data and "tags" in data["format"]:
                print("   📦 FORMAT TAGS:")
                for key, value in data["format"]["tags"].items():
                    if any(
                        date_word in key.lower()
                        for date_word in ["date", "time", "create", "record", "origin"]
                    ):
                        print(f"      🏷️  {key}: {value}")

            # Stream metadata
            if "streams" in data:
                for i, stream in enumerate(data["streams"]):
                    if "tags" in stream:
                        print(
                            f"   🎞️  STREAM {i} TAGS ({stream.get('codec_type', 'unknown')}):"
                        )
                        for key, value in stream["tags"].items():
                            if any(
                                date_word in key.lower()
                                for date_word in [
                                    "date",
                                    "time",
                                    "create",
                                    "record",
                                    "origin",
                                ]
                            ):
                                print(f"      🏷️  {key}: {value}")
        else:
            print(f"   ❌ FFprobe failed: {result.stderr}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 3. FFPROBE - FORMAT TAGS ONLY
    print("\n🏷️  3. FFPROBE - FORMAT TAGS (CSV):")
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "format_tags",
            "-of",
            "csv=p=0",
            str(file_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"   📋 Raw output: {result.stdout.strip()}")
        else:
            print(f"   ❌ Error: {result.stderr}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 4. PYMEDIAINFO - COMPREHENSIVE
    print("\n📊 4. PYMEDIAINFO - COMPREHENSIVE:")
    try:
        from pymediainfo import MediaInfo

        info = MediaInfo.parse(str(file_path))

        for track in info.tracks:
            print(f"   🎭 TRACK TYPE: {track.track_type}")
            track_data = track.to_data()

            # Find all date/time related fields
            date_fields = {}
            for key, value in track_data.items():
                if value and any(
                    date_word in key.lower()
                    for date_word in [
                        "date",
                        "time",
                        "create",
                        "record",
                        "origin",
                        "master",
                    ]
                ):
                    date_fields[key] = value

            if date_fields:
                for key, value in date_fields.items():
                    print(f"      📅 {key}: {value}")
            else:
                print("      ❌ No date fields found")
    except ImportError:
        print("   ⚠️  PyMediaInfo not available")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 5. EXIFTOOL (if available)
    print("\n🔍 5. EXIFTOOL:")
    try:
        cmd = ["exiftool", "-time:all", "-s", str(file_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if line.strip():
                    print(f"   📅 {line}")
        else:
            print(f"   ❌ ExifTool not available or failed")
    except FileNotFoundError:
        print("   ⚠️  ExifTool not installed")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 6. WINDOWS PROPERTY SYSTEM (if on Windows)
    print("\n🪟 6. WINDOWS PROPERTY SYSTEM:")
    if sys.platform == "win32":
        try:
            import win32api
            import win32con
            import win32file

            # Get extended file attributes
            attrs = win32api.GetFileAttributes(str(file_path))
            print(f"   🗂️  File Attributes: {attrs}")

            # Try to get creation time via Windows API
            handle = win32file.CreateFile(
                str(file_path),
                win32con.GENERIC_READ,
                win32con.FILE_SHARE_READ,
                None,
                win32con.OPEN_EXISTING,
                0,
                None,
            )
            creation_time, access_time, write_time = win32file.GetFileTime(handle)
            win32file.CloseHandle(handle)

            print(f"   📅 Windows Creation Time: {creation_time}")
            print(f"   📅 Windows Access Time: {access_time}")
            print(f"   📅 Windows Write Time: {write_time}")

        except ImportError:
            print("   ⚠️  Windows API modules not available")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    else:
        print("   ⚠️  Not on Windows")

    # 7. RAW HEX INSPECTION
    print("\n🔬 7. RAW METADATA INSPECTION:")
    try:
        with open(file_path, "rb") as f:
            # Read first 64KB to look for metadata chunks
            data = f.read(65536)

            # Look for common AVI metadata signatures
            signatures = [
                b"IDIT",  # Digitization time
                b"ICRD",  # Creation date
                b"ISFT",  # Software
                b"LIST",  # List chunk
                b"INFO",  # Info chunk
                b"date",  # Generic date
                b"creation_time",  # Creation time
            ]

            found_metadata = []
            for sig in signatures:
                pos = data.find(sig)
                if pos != -1:
                    # Extract some context around the signature
                    start = max(0, pos - 20)
                    end = min(len(data), pos + 50)
                    context = data[start:end]
                    # Convert to readable format
                    readable = "".join(
                        chr(b) if 32 <= b <= 126 else f"\\x{b:02x}" for b in context
                    )
                    found_metadata.append(
                        f"   🔍 Found {sig.decode('ascii', errors='ignore')} at offset {pos}: {readable}"
                    )

            if found_metadata:
                for item in found_metadata:
                    print(item)
            else:
                print("   ❌ No metadata signatures found in first 64KB")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 80)
    print("🎯 ANALYSIS COMPLETE!")
    print(
        "📋 Look for date fields that might correspond to Windows File Explorer 'Media created'"
    )
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python avi_metadata_analyzer.py <avi_file>")
        sys.exit(1)

    avi_file = sys.argv[1]
    if not os.path.exists(avi_file):
        print(f"Error: File not found: {avi_file}")
        sys.exit(1)

    analyze_avi_metadata(avi_file)
