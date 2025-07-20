#!/usr/bin/env python3
"""
Image and Video Organizer

Recursively processes images and videos, organizing them by creation date
and handling duplicates and naming conflicts.
"""

import argparse
import hashlib
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError:
    Image = None
    TAGS = None

try:
    import exifread
except ImportError:
    exifread = None

try:
    from pymediainfo import MediaInfo
except ImportError:
    MediaInfo = None


class ImageVideoOrganizer:
    """Main class for organizing images and videos by creation date."""

    # Supported file extensions
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

    def __init__(self, source_path: str, destination_path: str = None):
        """
        Initialize the organizer.

        Args:
            source_path: Path to scan for images/videos
            destination_path: Path to organize files to (defaults to source_path/organized)
        """
        self.source_path = Path(source_path)
        if not self.source_path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")

        self.destination_path = (
            Path(destination_path)
            if destination_path
            else self.source_path / "organized"
        )
        self.destination_path.mkdir(parents=True, exist_ok=True)

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
        self, file_path: Path, supported_extensions: Set[str]
    ) -> bool:
        """Check if a file is a supported media file."""
        return file_path.is_file() and file_path.suffix.lower() in supported_extensions

    def get_creation_date(self, file_path: Path) -> datetime:
        """
        Extract creation date from file metadata.

        Args:
            file_path: Path to the media file

        Returns:
            datetime object representing the creation date
        """
        # Try EXIF data for images
        if file_path.suffix.lower() in self.IMAGE_EXTENSIONS:
            date = self._get_image_creation_date(file_path)
            if date:
                return date

        # Try video metadata
        elif file_path.suffix.lower() in self.VIDEO_EXTENSIONS:
            date = self._get_video_creation_date(file_path)
            if date:
                return date

        # Fallback to file system dates
        return self._get_file_system_date(file_path)

    def _get_image_creation_date(self, file_path: Path) -> Optional[datetime]:
        """Extract creation date from image EXIF data."""
        creation_date = self._extract_date_with_pillow(file_path)
        if creation_date:
            return creation_date

        creation_date = self._extract_date_with_exifread(file_path)
        if creation_date:
            return creation_date

        return None

    def _extract_date_with_pillow(self, file_path: Path) -> Optional[datetime]:
        """Extract creation date using PIL library."""
        if not Image or not TAGS:
            return None

        try:
            with Image.open(file_path) as image:
                exif_data = image.getexif()
                if not exif_data:
                    return None

                for tag_identifier, tag_value in exif_data.items():
                    tag_name = TAGS.get(tag_identifier, tag_identifier)
                    if tag_name in [
                        "DateTime",
                        "DateTimeOriginal",
                        "DateTimeDigitized",
                    ]:
                        parsed_date = self._parse_exif_datetime(tag_value)
                        if parsed_date:
                            return parsed_date
        except Exception:
            pass

        return None

    def _extract_date_with_exifread(self, file_path: Path) -> Optional[datetime]:
        """Extract creation date using exifread library as fallback."""
        if not exifread:
            return None

        try:
            with open(file_path, "rb") as file_handle:
                exif_tags = exifread.process_file(file_handle)

                priority_tag_names = [
                    "EXIF DateTimeOriginal",
                    "EXIF DateTime",
                    "Image DateTime",
                ]
                for tag_name in priority_tag_names:
                    if tag_name in exif_tags:
                        date_string = str(exif_tags[tag_name])
                        parsed_date = self._parse_exif_datetime(date_string)
                        if parsed_date:
                            return parsed_date
        except Exception:
            pass

        return None

    def _parse_exif_datetime(self, date_string: str) -> Optional[datetime]:
        """Parse EXIF datetime string to datetime object."""
        try:
            return datetime.strptime(date_string, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            return None

    def _get_video_creation_date(self, file_path: Path) -> Optional[datetime]:
        """Extract creation date from video metadata."""
        if not MediaInfo:
            return None

        try:
            media_information = MediaInfo.parse(str(file_path))

            general_track = self._find_general_track(media_information)
            if general_track:
                return self._extract_date_from_video_track(general_track)
        except Exception:
            pass

        return None

    def _find_general_track(self, media_information):
        """Find the general track containing metadata in video file."""
        for track in media_information.tracks:
            if track.track_type == "General":
                return track
        return None

    def _extract_date_from_video_track(self, track) -> Optional[datetime]:
        """Extract creation date from video track metadata."""
        date_field_priority = ["recorded_date", "tagged_date", "encoded_date"]

        for field_name in date_field_priority:
            date_value = getattr(track, field_name, None)
            if date_value:
                parsed_date = self._parse_video_datetime(str(date_value))
                if parsed_date:
                    return parsed_date

        return None

    def _parse_video_datetime(self, date_string: str) -> Optional[datetime]:
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

    def _get_file_system_date(self, file_path: Path) -> datetime:
        """Get creation date from file system metadata."""
        file_statistics = file_path.stat()
        available_timestamps = self._collect_available_timestamps(file_statistics)
        earliest_timestamp = min(available_timestamps)

        return datetime.fromtimestamp(earliest_timestamp)

    def _collect_available_timestamps(self, file_statistics) -> List[float]:
        """Collect all available timestamps from file statistics."""
        timestamps = [file_statistics.st_mtime]  # Always include modification time

        if hasattr(file_statistics, "st_birthtime"):  # macOS
            timestamps.append(file_statistics.st_birthtime)
        elif os.name == "nt":  # Windows - st_ctime is creation time
            timestamps.append(file_statistics.st_ctime)

        return timestamps

    def format_date_folder(self, date: datetime) -> str:
        """Format datetime to YYYY_MM_DD folder name."""
        return date.strftime("%Y_%m_%d")

    def calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA-256 hash of a file for duplicate detection.

        Args:
            file_path: Path to the file

        Returns:
            Hexadecimal string representation of the file hash
        """
        file_hasher = hashlib.sha256()
        chunk_size = 4096

        with open(file_path, "rb") as file_handle:
            for data_chunk in iter(lambda: file_handle.read(chunk_size), b""):
                file_hasher.update(data_chunk)

        return file_hasher.hexdigest()

    def is_duplicate(self, file_path: Path, existing_hashes: Set[str]) -> bool:
        """
        Check if a file is a duplicate based on its hash.

        Args:
            file_path: Path to the file to check
            existing_hashes: Set of existing file hashes

        Returns:
            True if the file is a duplicate, False otherwise
        """
        file_hash = self.calculate_file_hash(file_path)
        return file_hash in existing_hashes

    def generate_unique_filename(
        self,
        destination_directory: Path,
        original_filename: str,
        source_file_path: Path,
    ) -> Optional[str]:
        """
        Generate a unique filename to avoid naming conflicts.

        Args:
            destination_directory: Directory where the file will be placed
            original_filename: Original filename
            source_file_path: Path to the source file being copied

        Returns:
            Unique filename that doesn't conflict with existing files, or None if file is duplicate
        """
        filename_without_extension = Path(original_filename).stem
        file_extension = Path(original_filename).suffix
        iteration_counter = 1

        while True:
            candidate_filename = self._create_candidate_filename(
                filename_without_extension,
                file_extension,
                iteration_counter,
                original_filename,
            )

            candidate_file_path = destination_directory / candidate_filename

            if not candidate_file_path.exists():
                return candidate_filename

            if self._is_same_file_content(candidate_file_path, source_file_path):
                return None  # Duplicate file, no need to copy

            iteration_counter += 1
            if iteration_counter > 999:  # Safety limit to prevent infinite loops
                raise ValueError(
                    f"Could not generate unique filename for {original_filename}"
                )

    def _create_candidate_filename(
        self, base_name: str, extension: str, counter: int, original: str
    ) -> str:
        """Create a candidate filename with appropriate counter suffix."""
        if counter == 1:
            return original
        else:
            return f"{base_name}_{counter:03d}{extension}"

    def _is_same_file_content(
        self, existing_file_path: Path, new_file_path: Path
    ) -> bool:
        """Check if two files have the same content by comparing their hashes."""
        try:
            existing_file_hash = self.calculate_file_hash(existing_file_path)
            new_file_hash = self.calculate_file_hash(new_file_path)
            return existing_file_hash == new_file_hash
        except (FileNotFoundError, PermissionError):
            # If we can't read files for comparison, assume they're different
            return False

    def organize_files(self) -> dict:
        """
        Main method to organize all found media files.

        Returns:
            Dictionary with organization statistics
        """
        discovered_media_files = self.find_media_files()
        organization_statistics = self._initialize_statistics(discovered_media_files)

        processed_file_hashes: Set[str] = set()
        files_organized_by_date: Dict[str, List[Path]] = {}

        for current_file_path in discovered_media_files:
            try:
                if self._should_skip_file(current_file_path, processed_file_hashes):
                    organization_statistics["duplicates_skipped"] += 1
                    continue

                processed_file_result = self._process_single_file(
                    current_file_path, processed_file_hashes, files_organized_by_date
                )

                self._update_statistics_from_file_result(
                    organization_statistics, processed_file_result
                )

            except Exception as error:
                print(f"Error processing {current_file_path}: {error}")
                organization_statistics["errors"] += 1
                continue

        self._finalize_statistics(organization_statistics, files_organized_by_date)
        return organization_statistics

    def _initialize_statistics(self, media_files: List[Path]) -> dict:
        """Initialize the organization statistics dictionary."""
        return {
            "total_files": len(media_files),
            "processed": 0,
            "duplicates_skipped": 0,
            "conflicts_resolved": 0,
            "errors": 0,
        }

    def _should_skip_file(self, file_path: Path, processed_hashes: Set[str]) -> bool:
        """Determine if a file should be skipped during organization."""
        if self.destination_path in file_path.parents:
            return True

        return self.is_duplicate(file_path, processed_hashes)

    def _process_single_file(
        self,
        file_path: Path,
        processed_hashes: Set[str],
        files_by_date: Dict[str, List[Path]],
    ) -> dict:
        """Process a single file for organization."""
        creation_date = self.get_creation_date(file_path)
        date_folder_name = self.format_date_folder(creation_date)

        destination_directory = self._create_date_directory(date_folder_name)
        unique_filename = self.generate_unique_filename(
            destination_directory, file_path.name, file_path
        )

        if unique_filename is None:
            return {"type": "duplicate"}

        conflict_resolved = unique_filename != file_path.name
        final_destination_path = destination_directory / unique_filename

        shutil.copy2(file_path, final_destination_path)

        file_hash = self.calculate_file_hash(file_path)
        processed_hashes.add(file_hash)

        self._track_file_by_date(
            files_by_date, date_folder_name, final_destination_path
        )

        return {"type": "processed", "conflict_resolved": conflict_resolved}

    def _create_date_directory(self, date_folder_name: str) -> Path:
        """Create and return the destination directory for a specific date."""
        destination_directory = self.destination_path / date_folder_name
        destination_directory.mkdir(parents=True, exist_ok=True)
        return destination_directory

    def _track_file_by_date(
        self, files_by_date: Dict[str, List[Path]], date_folder: str, file_path: Path
    ):
        """Track a file in the files_by_date dictionary."""
        if date_folder not in files_by_date:
            files_by_date[date_folder] = []
        files_by_date[date_folder].append(file_path)

    def _update_statistics_from_file_result(self, statistics: dict, result: dict):
        """Update statistics based on file processing result."""
        if result["type"] == "duplicate":
            statistics["duplicates_skipped"] += 1
        elif result["type"] == "processed":
            statistics["processed"] += 1
            if result.get("conflict_resolved", False):
                statistics["conflicts_resolved"] += 1

    def _finalize_statistics(
        self, statistics: dict, files_by_date: Dict[str, List[Path]]
    ):
        """Add final summary information to statistics."""
        statistics["date_folders_created"] = len(files_by_date)
        statistics["files_by_date"] = {
            date_folder: len(file_list)
            for date_folder, file_list in files_by_date.items()
        }


def main():
    """Main entry point for the script."""
    command_line_parser = argparse.ArgumentParser(
        description="Organize images and videos by creation date"
    )
    command_line_parser.add_argument(
        "source_path", help="Path to scan for images and videos"
    )
    command_line_parser.add_argument(
        "--destination", "-d", help="Destination path for organized files"
    )

    parsed_arguments = command_line_parser.parse_args()

    try:
        file_organizer = ImageVideoOrganizer(
            parsed_arguments.source_path, parsed_arguments.destination
        )
        organization_results = file_organizer.organize_files()

        print(f"Organization complete!")
        print(f"Total files found: {organization_results['total_files']}")
        print(f"Files processed: {organization_results['processed']}")
        print(f"Duplicates skipped: {organization_results['duplicates_skipped']}")
        print(f"Conflicts resolved: {organization_results['conflicts_resolved']}")
        print(f"Errors encountered: {organization_results['errors']}")
        print(f"Date folders created: {organization_results['date_folders_created']}")

        if organization_results.get("files_by_date"):
            print("\nFiles organized by date:")
            for date_folder_name, file_count in sorted(
                organization_results["files_by_date"].items()
            ):
                print(f"  {date_folder_name}: {file_count} files")

    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
