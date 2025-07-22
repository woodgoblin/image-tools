#!/usr/bin/env python3
"""
Metadata Time Changer

Changes EXIF, XMP, IPTC metadata timestamps and file modification dates
for images and videos using human-readable time adjustments.
"""

import argparse
import os
import re
import shutil
import struct
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import piexif
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError:
    Image = None
    TAGS = None
    piexif = None

try:
    from pymediainfo import MediaInfo
except ImportError:
    MediaInfo = None

try:
    import subprocess

    import ffmpeg
except ImportError:
    ffmpeg = None
    subprocess = None


class TimeParsingError(Exception):
    """Exception raised when time format cannot be parsed."""

    pass


class MetadataTimeChanger:
    """Main class for changing metadata timestamps in photos and videos."""

    # Supported file extensions (reuse from organizer)
    IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".tiff",
        ".tif",
        ".bmp",
        ".gif",
        ".webp",
    }
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v"}

    def __init__(self, source_path: str, time_adjustment: str, dry_run: bool = False):
        """
        Initialize the metadata time changer.

        Args:
            source_path: Path to scan for media files
            time_adjustment: Human-readable time adjustment (e.g., '+1y 2m 3d')
            dry_run: If True, only show what would be changed without modifying files
        """
        self.source_path = Path(source_path)
        if not self.source_path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")

        self.time_adjustment_string = time_adjustment
        self.time_delta = self.parse_time_adjustment(time_adjustment)
        self.dry_run = dry_run
        self.errors: List[str] = []

    def parse_time_adjustment(self, time_string: str) -> timedelta:
        """
        Parse human-readable time adjustment string to timedelta.

        Supports formats like:
        - +5 (days)
        - +1y 2m 3d (1 year, 2 months, 3 days)
        - -2w 1d (subtract 2 weeks, 1 day)

        Args:
            time_string: Human-readable time adjustment string

        Returns:
            timedelta object representing the time adjustment

        Raises:
            TimeParsingError: If the format cannot be parsed
        """
        time_string = time_string.strip()

        # Check if it starts with + or -
        if not time_string.startswith(("+", "-")):
            raise TimeParsingError(
                f"Time adjustment must start with + or -: {time_string}"
            )

        is_positive = time_string.startswith("+")
        time_string = time_string[1:]  # Remove the +/- sign

        # If it's just a number, assume days
        if time_string.isdigit():
            days = int(time_string)
            return timedelta(days=days if is_positive else -days)

        # Parse complex format like "1y 2m 3d 4w 5h"
        pattern = r"(\d+)([a-zA-Z])"
        matches = re.findall(pattern, time_string.lower())

        if not matches:
            raise TimeParsingError(f"Invalid time format: {time_string}")

        total_days = 0

        for value_str, unit in matches:
            value = int(value_str)

            if unit == "y":  # years
                total_days += value * 365  # Approximate, ignoring leap years
            elif unit == "m":  # months
                total_days += value * 30  # Approximate month length
            elif unit == "w":  # weeks
                total_days += value * 7
            elif unit == "d":  # days
                total_days += value
            elif unit == "h":  # hours (convert to fraction of days)
                total_days += value / 24
            else:
                raise TimeParsingError(f"Unsupported time unit: {unit}")

        return timedelta(days=total_days if is_positive else -total_days)

    def find_media_files(self) -> List[Path]:
        """
        Recursively find all supported image and video files.

        Returns:
            List of Path objects for found media files
        """
        discovered_media_files = []
        all_supported_extensions = self.IMAGE_EXTENSIONS | self.VIDEO_EXTENSIONS

        for current_file_path in self.source_path.rglob("*"):
            if self._is_supported_media_file(
                current_file_path, all_supported_extensions
            ):
                discovered_media_files.append(current_file_path)

        return discovered_media_files

    def _is_supported_media_file(
        self, file_path: Path, supported_extensions: set
    ) -> bool:
        """Check if a file is a supported media file."""
        return file_path.is_file() and file_path.suffix.lower() in supported_extensions

    def read_photo_metadata_timestamps(
        self, file_path: Path
    ) -> Dict[str, Optional[datetime]]:
        """
        Read all timestamp metadata from a photo file.

        Args:
            file_path: Path to the photo file

        Returns:
            Dictionary with timestamp field names and their datetime values
        """
        timestamps = {}

        # Try reading EXIF data with piexif
        if piexif:
            try:
                exif_dict = piexif.load(str(file_path))
                timestamps.update(self._extract_exif_timestamps_piexif(exif_dict))
            except Exception as e:
                self.errors.append(f"Could not read EXIF from {file_path}: {e}")

        # Also try with PIL for additional metadata
        if Image and TAGS:
            try:
                with Image.open(file_path) as image:
                    exif_data = image.getexif()
                    timestamps.update(self._extract_exif_timestamps_pil(exif_data))
            except Exception as e:
                self.errors.append(f"Could not read PIL EXIF from {file_path}: {e}")

        return timestamps

    def _extract_exif_timestamps_piexif(
        self, exif_dict: dict
    ) -> Dict[str, Optional[datetime]]:
        """Extract timestamp fields from piexif EXIF dictionary."""
        timestamps = {}

        # EXIF timestamp fields to check
        exif_fields = {
            piexif.ExifIFD.DateTimeOriginal: "DateTimeOriginal",
            piexif.ExifIFD.DateTimeDigitized: "DateTimeDigitized",
            piexif.ImageIFD.DateTime: "DateTime",
        }

        for field_id, field_name in exif_fields.items():
            try:
                # Check in EXIF IFD
                if "Exif" in exif_dict and field_id in exif_dict["Exif"]:
                    date_str = exif_dict["Exif"][field_id].decode("utf-8")
                    timestamps[field_name] = self._parse_exif_datetime_string(date_str)
                # Check in Image IFD for DateTime
                elif (
                    field_id == piexif.ImageIFD.DateTime
                    and "0th" in exif_dict
                    and field_id in exif_dict["0th"]
                ):
                    date_str = exif_dict["0th"][field_id].decode("utf-8")
                    timestamps[field_name] = self._parse_exif_datetime_string(date_str)
            except Exception:
                timestamps[field_name] = None

        return timestamps

    def _extract_exif_timestamps_pil(
        self, exif_data: dict
    ) -> Dict[str, Optional[datetime]]:
        """Extract timestamp fields from PIL EXIF data."""
        timestamps = {}

        target_tags = ["DateTime", "DateTimeOriginal", "DateTimeDigitized"]

        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            if tag_name in target_tags and tag_name not in timestamps:
                timestamps[tag_name] = self._parse_exif_datetime_string(str(value))

        return timestamps

    def _parse_exif_datetime_string(self, date_string: str) -> Optional[datetime]:
        """Parse EXIF datetime string to datetime object."""
        try:
            return datetime.strptime(date_string, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            return None

    def read_video_metadata_timestamps(
        self, file_path: Path
    ) -> Dict[str, Optional[datetime]]:
        """
        Read all timestamp metadata from a video file.

        Args:
            file_path: Path to the video file

        Returns:
            Dictionary with timestamp field names and their datetime values
        """
        timestamps = {}

        if not MediaInfo:
            return timestamps

        try:
            media_info = MediaInfo.parse(str(file_path))

            for track in media_info.tracks:
                if track.track_type == "General":
                    # Common video timestamp fields
                    timestamp_fields = [
                        "recorded_date",
                        "tagged_date",
                        "encoded_date",
                        "mastered_date",
                        "file_last_modification_date",
                        "creation_time",
                        "date",
                    ]

                    for field_name in timestamp_fields:
                        try:
                            field_value = getattr(track, field_name, None)
                            if field_value:
                                timestamps[field_name] = (
                                    self._parse_video_datetime_string(str(field_value))
                                )
                            else:
                                timestamps[field_name] = None
                        except Exception:
                            timestamps[field_name] = None

        except Exception as e:
            self.errors.append(f"Could not read video metadata from {file_path}: {e}")

        return timestamps

    def _parse_video_datetime_string(self, date_string: str) -> Optional[datetime]:
        """Parse video metadata datetime string to datetime object."""
        try:
            # Handle UTC timestamp format
            if "UTC" in date_string:
                cleaned_date_string = date_string.replace(" UTC", "")
                return datetime.strptime(cleaned_date_string, "%Y-%m-%d %H:%M:%S")

            # Handle ISO format
            iso_formatted_string = date_string.replace("T", " ").replace("Z", "")
            return datetime.fromisoformat(iso_formatted_string)
        except ValueError:
            return None

    def get_file_system_timestamps(self, file_path: Path) -> Dict[str, datetime]:
        """
        Get file system timestamps.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with file system timestamp names and values
        """
        file_stat = file_path.stat()
        timestamps = {"modification_time": datetime.fromtimestamp(file_stat.st_mtime)}

        # Add creation time if available
        if hasattr(file_stat, "st_birthtime"):  # macOS
            timestamps["creation_time"] = datetime.fromtimestamp(file_stat.st_birthtime)
        elif os.name == "nt":  # Windows
            timestamps["creation_time"] = datetime.fromtimestamp(file_stat.st_ctime)

        return timestamps

    def adjust_timestamps(
        self, timestamps: Dict[str, Optional[datetime]]
    ) -> Dict[str, Optional[datetime]]:
        """
        Apply time adjustment to a dictionary of timestamps.

        Args:
            timestamps: Dictionary with timestamp field names and datetime values

        Returns:
            Dictionary with adjusted timestamp values
        """
        adjusted_timestamps = {}

        for field_name, timestamp_value in timestamps.items():
            if timestamp_value is not None:
                try:
                    adjusted_timestamps[field_name] = timestamp_value + self.time_delta
                except Exception as e:
                    self.errors.append(f"Could not adjust timestamp {field_name}: {e}")
                    adjusted_timestamps[field_name] = timestamp_value
            else:
                adjusted_timestamps[field_name] = None

        return adjusted_timestamps

    def write_photo_metadata_timestamps(
        self, file_path: Path, timestamps: Dict[str, Optional[datetime]]
    ) -> bool:
        """
        Write adjusted timestamps back to photo metadata.

        Args:
            file_path: Path to the photo file
            timestamps: Dictionary with adjusted timestamp values

        Returns:
            True if successful, False otherwise
        """
        if not piexif:
            self.errors.append(
                f"piexif not available for writing metadata to {file_path}"
            )
            return False

        try:
            # Load existing EXIF data
            exif_dict = piexif.load(str(file_path))

            # Update timestamp fields
            for field_name, timestamp_value in timestamps.items():
                if timestamp_value is not None:
                    formatted_timestamp = timestamp_value.strftime("%Y:%m:%d %H:%M:%S")

                    if field_name == "DateTimeOriginal":
                        exif_dict["Exif"][
                            piexif.ExifIFD.DateTimeOriginal
                        ] = formatted_timestamp
                    elif field_name == "DateTimeDigitized":
                        exif_dict["Exif"][
                            piexif.ExifIFD.DateTimeDigitized
                        ] = formatted_timestamp
                    elif field_name == "DateTime":
                        exif_dict["0th"][piexif.ImageIFD.DateTime] = formatted_timestamp

            # Write back to file
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, str(file_path))

            return True

        except Exception as e:
            self.errors.append(f"Could not write EXIF metadata to {file_path}: {e}")
            return False

    def write_video_metadata_timestamps(
        self, file_path: Path, timestamps: Dict[str, Optional[datetime]]
    ) -> bool:
        """
        Write adjusted timestamps back to video metadata.
        For AVI files, uses safe append-only RIFF INFO chunk writer.
        For other formats, uses ffmpeg.

        Args:
            file_path: Path to the video file
            timestamps: Dictionary with adjusted timestamp values

        Returns:
            True if successful, False otherwise
        """
        # Find the most relevant timestamp to use
        primary_timestamp = None

        # Priority order: creation_time, recorded_date, date, encoded_date
        timestamp_priority = [
            "creation_time",
            "recorded_date",
            "date",
            "encoded_date",
            "tagged_date",
            "mastered_date",
        ]

        for field_name in timestamp_priority:
            if field_name in timestamps and timestamps[field_name] is not None:
                primary_timestamp = timestamps[field_name]
                break

        if primary_timestamp is None:
            return False

        # Use safe in-place modifier for AVI files (changes existing dates only)
        if file_path.suffix.lower() == ".avi":
            return self.write_avi_metadata_safe_inplace_modify(
                file_path, primary_timestamp
            )

        # Use ffmpeg for other video formats
        return self.write_video_metadata_with_ffmpeg(file_path, primary_timestamp)

    def write_video_metadata_with_ffmpeg(
        self, file_path: Path, timestamp: datetime
    ) -> bool:
        """
        Write video metadata using ffmpeg with proper metadata preservation.
        Only modifies date fields, preserves all other existing metadata.

        Args:
            file_path: Path to the video file
            timestamp: Adjusted timestamp to write

        Returns:
            True if successful, False otherwise
        """
        if not ffmpeg or not subprocess:
            self.errors.append(
                f"ffmpeg not available for writing video metadata to {file_path}"
            )
            return False

        # Check if ffmpeg is installed on the system
        if not shutil.which("ffmpeg"):
            self.errors.append(
                f"ffmpeg binary not found - cannot modify video metadata for {file_path}"
            )
            return False

        try:
            if self.dry_run:
                return True

            # Create temporary output file
            temp_output = file_path.with_suffix(f".tmp{file_path.suffix}")

            # Format timestamp for video metadata
            formatted_timestamp = timestamp.strftime("%Y-%m-%dT%H:%M:%S")

            # Build ffmpeg command that preserves existing metadata
            cmd = [
                "ffmpeg",
                "-i",
                str(file_path),
                "-c",
                "copy",  # Copy streams without re-encoding
                "-map_metadata",
                "0",  # Preserve all existing metadata
                "-metadata",
                f"creation_time={formatted_timestamp}",
                "-metadata",
                f"date={formatted_timestamp}",
                "-y",  # Overwrite output file
                str(temp_output),
            ]

            # Execute ffmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Replace original file with modified version
            if temp_output.exists():
                # Create backup
                backup_file = file_path.with_suffix(f".backup{file_path.suffix}")
                file_path.rename(backup_file)

                # Move new file to original location
                temp_output.rename(file_path)

                # Remove backup
                backup_file.unlink()

                return True
            else:
                self.errors.append(
                    f"ffmpeg failed to create output file for {file_path}"
                )
                return False

        except subprocess.CalledProcessError as e:
            self.errors.append(f"ffmpeg command failed for {file_path}: {e.stderr}")
            return False
        except Exception as e:
            self.errors.append(f"Failed to write video metadata to {file_path}: {e}")
            return False
        finally:
            # Clean up temporary files if they exist
            temp_output = file_path.with_suffix(f".tmp{file_path.suffix}")
            if temp_output.exists():
                temp_output.unlink()

    def set_file_system_timestamps(
        self, file_path: Path, timestamps: Dict[str, datetime]
    ) -> bool:
        """
        Set file system timestamps.
        Sets creation time equal to modification time for consistency.
        Uses modification time as primary source since it's more reliable.

        Args:
            file_path: Path to the file
            timestamps: Dictionary with adjusted file system timestamps

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use modification time as the primary timestamp (more reliable)
            target_timestamp = None

            if (
                "modification_time" in timestamps
                and timestamps["modification_time"] is not None
            ):
                target_timestamp = timestamps["modification_time"]
            elif (
                "creation_time" in timestamps
                and timestamps["creation_time"] is not None
            ):
                target_timestamp = timestamps["creation_time"]

            if target_timestamp is not None:
                timestamp_value = target_timestamp.timestamp()
                # Set both access time and modification time to the same value
                os.utime(file_path, (timestamp_value, timestamp_value))

            return True

        except Exception as e:
            self.errors.append(
                f"Could not set file system timestamps for {file_path}: {e}"
            )
            return False

    def process_single_file(self, file_path: Path) -> Dict[str, any]:
        """
        Process a single media file: read timestamps, adjust them, and write back.

        Args:
            file_path: Path to the media file

        Returns:
            Dictionary with processing results
        """
        result = {
            "file_path": file_path,
            "processed": False,
            "metadata_updated": False,
            "filesystem_updated": False,
            "original_timestamps": {},
            "adjusted_timestamps": {},
        }

        try:
            # Read current timestamps
            if file_path.suffix.lower() in self.IMAGE_EXTENSIONS:
                original_metadata_timestamps = self.read_photo_metadata_timestamps(
                    file_path
                )
            elif file_path.suffix.lower() in self.VIDEO_EXTENSIONS:
                original_metadata_timestamps = self.read_video_metadata_timestamps(
                    file_path
                )
            else:
                original_metadata_timestamps = {}

            original_filesystem_timestamps = self.get_file_system_timestamps(file_path)

            result["original_timestamps"] = {
                "metadata": original_metadata_timestamps,
                "filesystem": original_filesystem_timestamps,
            }

            # Adjust timestamps
            adjusted_metadata_timestamps = self.adjust_timestamps(
                original_metadata_timestamps
            )
            adjusted_filesystem_timestamps = self.adjust_timestamps(
                original_filesystem_timestamps
            )

            # Make creation time equal to modification time for consistency
            if (
                "modification_time" in adjusted_filesystem_timestamps
                and adjusted_filesystem_timestamps["modification_time"] is not None
            ):
                adjusted_filesystem_timestamps["creation_time"] = (
                    adjusted_filesystem_timestamps["modification_time"]
                )

            result["adjusted_timestamps"] = {
                "metadata": adjusted_metadata_timestamps,
                "filesystem": adjusted_filesystem_timestamps,
            }

            # In dry-run mode, don't actually write anything
            if self.dry_run:
                result["processed"] = True
                result["metadata_updated"] = True  # Would be updated
                result["filesystem_updated"] = True  # Would be updated
                return result

            # Write back metadata if there are any timestamps to update
            # For AVI files, always try to write metadata even if none existed originally
            should_write_metadata = any(
                ts is not None for ts in adjusted_metadata_timestamps.values()
            ) or (file_path.suffix.lower() == ".avi")

            if should_write_metadata:
                if file_path.suffix.lower() in self.IMAGE_EXTENSIONS:
                    result["metadata_updated"] = self.write_photo_metadata_timestamps(
                        file_path, adjusted_metadata_timestamps
                    )
                elif file_path.suffix.lower() in self.VIDEO_EXTENSIONS:
                    # For videos with no existing metadata, use adjusted filesystem time
                    if all(ts is None for ts in adjusted_metadata_timestamps.values()):
                        adjusted_metadata_timestamps["creation_time"] = (
                            adjusted_filesystem_timestamps["modification_time"]
                        )

                    result["metadata_updated"] = self.write_video_metadata_timestamps(
                        file_path, adjusted_metadata_timestamps
                    )
                else:
                    result["metadata_updated"] = False

            # Set file system timestamps
            result["filesystem_updated"] = self.set_file_system_timestamps(
                file_path, adjusted_filesystem_timestamps
            )

            result["processed"] = True

        except Exception as e:
            self.errors.append(f"Error processing file {file_path}: {e}")
            result["processed"] = False

        return result

    def write_avi_metadata_safe_inplace_modify(
        self, file_path: Path, timestamp: datetime
    ) -> bool:
        """
        RIFF-preserving AVI metadata modification that directly modifies IDIT chunk bytes.
        This preserves Windows File Explorer compatibility by maintaining container structure.

        Args:
            file_path: Path to the AVI file
            timestamp: Adjusted timestamp to write

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.dry_run:
                return True

            # Import required modules
            import shutil

            # Create backup first
            backup_path = file_path.with_suffix(".backup.avi")
            shutil.copy2(file_path, backup_path)

            try:
                # Read the entire file
                with open(file_path, "rb") as f:
                    data = bytearray(f.read())

                # Find IDIT chunk
                idit_pos, date_data = self._find_idit_chunk(data)
                if idit_pos is None:
                    self.errors.append(f"No IDIT chunk found in {file_path}")
                    # Clean up backup before returning
                    if backup_path.exists():
                        backup_path.unlink()
                    return False

                # Parse current date
                current_date_str = date_data.decode("ascii", errors="ignore")
                current_date = self._parse_canon_date(current_date_str)
                if current_date is None:
                    self.errors.append(f"Could not parse current date in {file_path}")
                    if backup_path.exists():
                        backup_path.unlink()
                    return False

                # Calculate new date (use the provided timestamp)
                new_date_str = self._format_canon_date(timestamp)
                new_date_bytes = new_date_str.encode("ascii")

                # Pad or truncate to match original chunk size
                original_size = len(date_data)
                if len(new_date_bytes) < original_size:
                    # Pad with null bytes
                    new_date_bytes += b"\x00" * (original_size - len(new_date_bytes))
                elif len(new_date_bytes) > original_size:
                    # Truncate if too long
                    new_date_bytes = new_date_bytes[:original_size]

                # Replace the date data in the file
                date_start = idit_pos + 8
                date_end = date_start + original_size
                data[date_start:date_end] = new_date_bytes

                # Write the modified data back
                with open(file_path, "wb") as f:
                    f.write(data)

                # Clean up backup if successful
                if backup_path.exists():
                    backup_path.unlink()
                return True

            except Exception as e:
                self.errors.append(f"RIFF modification failed for {file_path}: {e}")
                # Restore from backup
                if backup_path.exists():
                    shutil.copy2(backup_path, file_path)
                    backup_path.unlink()
                return False

        except Exception as e:
            self.errors.append(
                f"RIFF-preserving AVI modifier failed for {file_path}: {e}"
            )
            return False

    def _find_idit_chunk(self, data):
        """Find IDIT chunk in AVI RIFF data."""
        # Look for IDIT signature
        pos = data.find(b"IDIT")
        if pos == -1:
            return None, None

        # IDIT chunk structure: IDIT + 4-byte size + data
        if pos + 4 >= len(data):
            return None, None

        import struct

        chunk_size = struct.unpack("<L", data[pos + 4 : pos + 8])[0]

        # Get the actual date data
        date_start = pos + 8
        date_end = date_start + chunk_size

        if date_end > len(data):
            return None, None

        date_data = data[date_start:date_end]

        return (pos, date_data)

    def _parse_canon_date(self, date_str):
        """Parse Canon date format: 'MON AUG 28 14:14:28 2006'"""
        try:
            # Remove null bytes and extra whitespace
            clean_date = date_str.strip().rstrip("\x00").strip()

            # Parse the date format used by Canon
            dt = datetime.strptime(clean_date, "%a %b %d %H:%M:%S %Y")
            return dt
        except ValueError as e:
            self.errors.append(f"Could not parse Canon date '{clean_date}': {e}")
            return None

    def _format_canon_date(self, dt):
        """Format date in Canon format: 'MON AUG 28 14:14:28 2006'"""
        return dt.strftime("%a %b %d %H:%M:%S %Y").upper()


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Change metadata timestamps in photos and videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/photos +5          # Add 5 days
  %(prog)s /path/to/photos "+1y 2m"    # Add 1 year and 2 months  
  %(prog)s /path/to/photos "-2w 3d"    # Subtract 2 weeks and 3 days
  %(prog)s /path/to/photos +10 --dry-run  # Preview changes without modifying

Supported time units:
  y = years, m = months, w = weeks, d = days, h = hours
        """,
    )

    parser.add_argument("source_path", help="Path to scan for media files")
    parser.add_argument(
        "time_adjustment",
        help="Time adjustment (e.g., '+1y 2m 3d', '-5d', '+10'). Use quotes for negative values.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )

    parsed_arguments = parser.parse_args()

    try:
        changer = MetadataTimeChanger(
            parsed_arguments.source_path,
            parsed_arguments.time_adjustment,
            parsed_arguments.dry_run,
        )

        print(f"Time adjustment: {parsed_arguments.time_adjustment}")
        print(f"Parsed as: {changer.time_delta}")
        print(f"Dry run: {'Yes' if parsed_arguments.dry_run else 'No'}")
        print()

        media_files = changer.find_media_files()
        print(f"Found {len(media_files)} media files")

        if len(media_files) == 0:
            print("No media files found to process.")
            return

        print(
            f"{'Would process' if parsed_arguments.dry_run else 'Processing'} files..."
        )
        print()

        # Process all files
        processed_count = 0
        metadata_updated_count = 0
        filesystem_updated_count = 0

        for file_path in media_files:
            result = changer.process_single_file(file_path)

            if result["processed"]:
                processed_count += 1

                if result["metadata_updated"]:
                    metadata_updated_count += 1

                if result["filesystem_updated"]:
                    filesystem_updated_count += 1

                # Show verbose output for each file
                print(
                    f"{'[DRY RUN] ' if parsed_arguments.dry_run else ''}Processing: {file_path}"
                )

                # Show original timestamps
                original_meta = result["original_timestamps"]["metadata"]
                original_fs = result["original_timestamps"]["filesystem"]

                if any(ts is not None for ts in original_meta.values()):
                    print("  Original metadata timestamps:")
                    for field, timestamp in original_meta.items():
                        if timestamp is not None:
                            print(f"    {field}: {timestamp}")

                if original_fs:
                    print("  Original filesystem timestamps:")
                    for field, timestamp in original_fs.items():
                        print(f"    {field}: {timestamp}")

                # Show adjusted timestamps
                adjusted_meta = result["adjusted_timestamps"]["metadata"]
                adjusted_fs = result["adjusted_timestamps"]["filesystem"]

                if any(ts is not None for ts in adjusted_meta.values()):
                    print("  Adjusted metadata timestamps:")
                    for field, timestamp in adjusted_meta.items():
                        if timestamp is not None:
                            print(f"    {field}: {timestamp}")

                if adjusted_fs:
                    print("  Adjusted filesystem timestamps:")
                    for field, timestamp in adjusted_fs.items():
                        print(f"    {field}: {timestamp}")

                print()

        # Show summary
        print("=" * 60)
        print(f"{'DRY RUN ' if parsed_arguments.dry_run else ''}SUMMARY:")
        print(f"Total files processed: {processed_count}")
        print(
            f"Files with metadata {'would be ' if parsed_arguments.dry_run else ''}updated: {metadata_updated_count}"
        )
        print(
            f"Files with filesystem timestamps {'would be ' if parsed_arguments.dry_run else ''}updated: {filesystem_updated_count}"
        )

        # Show errors in red if any
        if changer.errors:
            print()
            print(
                f"\033[91mERRORS ENCOUNTERED ({len(changer.errors)}):\033[0m"
            )  # Red text
            for error in changer.errors:
                print(f"\033[91m  {error}\033[0m")  # Red text

    except (ValueError, TimeParsingError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
