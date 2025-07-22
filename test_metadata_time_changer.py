#!/usr/bin/env python3
"""
Tests for the metadata_time_changer module.
"""

import os
import shutil
import struct
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from metadata_time_changer import MetadataTimeChanger, TimeParsingError


class TestTimeParsingFunctionality:
    """Test suite for time parsing functionality."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.test_directory = Path(tempfile.mkdtemp())
        # Create a dummy file to satisfy source_path validation
        (self.test_directory / "dummy.jpg").touch()

    def teardown_method(self):
        """Clean up after each test."""
        shutil.rmtree(self.test_directory)

    def test_parse_simple_positive_days(self):
        """Parse simple positive day adjustment."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+5")

        # Act & Assert
        assert changer.time_delta == timedelta(days=5)

    def test_parse_simple_negative_days(self):
        """Parse simple negative day adjustment."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "-10")

        # Act & Assert
        assert changer.time_delta == timedelta(days=-10)

    def test_parse_complex_positive_format(self):
        """Parse complex positive time format with multiple units."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1y 2m 3d")

        # Act & Assert
        expected_days = 1 * 365 + 2 * 30 + 3  # 365 + 60 + 3 = 428 days
        assert changer.time_delta == timedelta(days=expected_days)

    def test_parse_complex_negative_format(self):
        """Parse complex negative time format with multiple units."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "-2w 1d")

        # Act & Assert
        expected_days = -(2 * 7 + 1)  # -15 days
        assert changer.time_delta == timedelta(days=expected_days)

    def test_parse_weeks_and_hours(self):
        """Parse time format with weeks and hours."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1w 12h")

        # Act & Assert
        expected_days = 7 + 12 / 24  # 7.5 days
        assert changer.time_delta == timedelta(days=expected_days)

    def test_parse_months_only(self):
        """Parse time format with months only."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+6m")

        # Act & Assert
        expected_days = 6 * 30  # 180 days
        assert changer.time_delta == timedelta(days=expected_days)

    def test_parse_years_only(self):
        """Parse time format with years only."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "-2y")

        # Act & Assert
        expected_days = -(2 * 365)  # -730 days
        assert changer.time_delta == timedelta(days=expected_days)

    def test_parse_case_insensitive(self):
        """Parse time format is case insensitive."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1Y 2M 3D")

        # Act & Assert
        expected_days = 1 * 365 + 2 * 30 + 3  # 428 days
        assert changer.time_delta == timedelta(days=expected_days)

    def test_parse_invalid_format_no_sign(self):
        """Parse invalid format without plus or minus sign raises error."""
        # Act & Assert
        with pytest.raises(TimeParsingError, match="Time adjustment must start with"):
            MetadataTimeChanger(str(self.test_directory), "5d")

    def test_parse_invalid_format_empty_after_sign(self):
        """Parse invalid format with empty string after sign raises error."""
        # Act & Assert
        with pytest.raises(TimeParsingError, match="Invalid time format"):
            MetadataTimeChanger(str(self.test_directory), "+")

    def test_parse_invalid_format_unsupported_unit(self):
        """Parse invalid format with unsupported time unit raises error."""
        # Act & Assert
        with pytest.raises(TimeParsingError, match="Unsupported time unit"):
            MetadataTimeChanger(str(self.test_directory), "+5x")

    def test_parse_invalid_format_malformed(self):
        """Parse malformed time format raises error."""
        # Act & Assert
        with pytest.raises(TimeParsingError, match="Invalid time format"):
            MetadataTimeChanger(str(self.test_directory), "+abc")

    def test_dry_run_flag_set_correctly(self):
        """Dry run flag is set correctly during initialization."""
        # Arrange & Act
        changer_dry = MetadataTimeChanger(str(self.test_directory), "+5", dry_run=True)
        changer_normal = MetadataTimeChanger(
            str(self.test_directory), "+5", dry_run=False
        )

        # Assert
        assert changer_dry.dry_run is True
        assert changer_normal.dry_run is False


class TestFileDiscoveryFunctionality:
    """Test suite for file discovery functionality."""

    def setup_method(self):
        """Set up test environment with various media files."""
        self.test_directory = Path(tempfile.mkdtemp())
        self.setup_test_media_files()

    def teardown_method(self):
        """Clean up after each test."""
        shutil.rmtree(self.test_directory)

    def setup_test_media_files(self):
        """Create test file structure with various media files."""
        # Create subdirectories
        (self.test_directory / "photos").mkdir()
        (self.test_directory / "videos").mkdir()

        # Create test files
        test_file_names = [
            "photo1.jpg",
            "photo2.PNG",
            "photo3.tiff",
            "video1.mp4",
            "video2.MOV",
            "video3.avi",
            "document.txt",  # Should be ignored
            "photos/nested_photo.jpeg",
            "videos/nested_video.mkv",
            "no_extension",  # Should be ignored
        ]

        for relative_file_path in test_file_names:
            complete_file_path = self.test_directory / relative_file_path
            complete_file_path.touch()

    def test_find_media_files_discovers_all_supported_formats(self):
        """Find media files discovers all supported image and video formats."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1")

        # Act
        discovered_media_files = changer.find_media_files()

        # Assert
        expected_media_files = {
            "photo1.jpg",
            "photo2.PNG",
            "photo3.tiff",
            "video1.mp4",
            "video2.MOV",
            "video3.avi",
            "photos/nested_photo.jpeg",
            "videos/nested_video.mkv",
        }

        found_relative_file_paths = {
            str(file_path.relative_to(self.test_directory)).replace("\\", "/")
            for file_path in discovered_media_files
        }

        assert len(discovered_media_files) == 8
        assert found_relative_file_paths == expected_media_files

    def test_find_media_files_case_insensitive_extensions(self):
        """Find media files handles case insensitive file extensions."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1")

        # Act
        discovered_media_files = changer.find_media_files()

        # Assert
        png_files = [f for f in discovered_media_files if f.suffix.lower() == ".png"]
        mov_files = [f for f in discovered_media_files if f.suffix.lower() == ".mov"]

        assert len(png_files) == 1  # photo2.PNG
        assert len(mov_files) == 1  # video2.MOV

    def test_find_media_files_ignores_unsupported_formats(self):
        """Find media files ignores unsupported file formats."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1")

        # Act
        discovered_media_files = changer.find_media_files()

        # Assert
        file_names = [f.name for f in discovered_media_files]
        assert "document.txt" not in file_names
        assert "no_extension" not in file_names


class TestMetadataTimeChangerInitialization:
    """Test suite for MetadataTimeChanger initialization."""

    def test_initialization_with_valid_path(self):
        """Initialize with valid source path succeeds."""
        # Arrange
        test_directory = Path(tempfile.mkdtemp())
        try:
            # Act
            changer = MetadataTimeChanger(str(test_directory), "+5")

            # Assert
            assert changer.source_path == test_directory
            assert changer.time_adjustment_string == "+5"
            assert changer.dry_run is False
            assert changer.errors == []
        finally:
            shutil.rmtree(test_directory)

    def test_initialization_with_invalid_path_raises_error(self):
        """Initialize with invalid source path raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Source path does not exist"):
            MetadataTimeChanger("/nonexistent/path", "+5")


class TestMetadataReadingFunctionality:
    """Test suite for metadata reading functionality."""

    def setup_method(self):
        """Set up test environment for metadata reading tests."""
        self.test_directory = Path(tempfile.mkdtemp())
        self.setup_test_media_files()

    def teardown_method(self):
        """Clean up after each test."""
        shutil.rmtree(self.test_directory)

    def setup_test_media_files(self):
        """Create test media files for metadata testing."""
        # Create test image file (empty for now)
        test_image = self.test_directory / "test_image.jpg"
        test_image.write_bytes(b"fake image data")

        # Create test video file (empty for now)
        test_video = self.test_directory / "test_video.mp4"
        test_video.write_bytes(b"fake video data")

    def test_read_photo_metadata_timestamps_handles_missing_metadata(self):
        """Read photo metadata handles files without EXIF data gracefully."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1")
        test_image = self.test_directory / "test_image.jpg"

        # Act
        timestamps = changer.read_photo_metadata_timestamps(test_image)

        # Assert
        assert isinstance(timestamps, dict)
        # For a fake image file, we expect None values or empty dict
        for timestamp_value in timestamps.values():
            assert timestamp_value is None or isinstance(timestamp_value, type(None))

    def test_read_video_metadata_timestamps_handles_missing_metadata(self):
        """Read video metadata handles files without metadata gracefully."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1")
        test_video = self.test_directory / "test_video.mp4"

        # Act
        timestamps = changer.read_video_metadata_timestamps(test_video)

        # Assert
        assert isinstance(timestamps, dict)
        # For a fake video file, we expect None values or empty dict

    def test_get_file_system_timestamps_returns_valid_timestamps(self):
        """Get file system timestamps returns valid datetime objects."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1")
        test_file = self.test_directory / "test_image.jpg"

        # Act
        timestamps = changer.get_file_system_timestamps(test_file)

        # Assert
        assert "modification_time" in timestamps
        assert isinstance(timestamps["modification_time"], datetime)

        # Should have creation_time on Windows
        if os.name == "nt":
            assert "creation_time" in timestamps
            assert isinstance(timestamps["creation_time"], datetime)

    def test_parse_exif_datetime_string_valid_format(self):
        """Parse EXIF datetime string with valid format succeeds."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1")
        valid_exif_datetime = "2023:12:25 14:30:45"

        # Act
        parsed_datetime = changer._parse_exif_datetime_string(valid_exif_datetime)

        # Assert
        assert parsed_datetime is not None
        assert parsed_datetime.year == 2023
        assert parsed_datetime.month == 12
        assert parsed_datetime.day == 25
        assert parsed_datetime.hour == 14
        assert parsed_datetime.minute == 30
        assert parsed_datetime.second == 45

    def test_parse_exif_datetime_string_invalid_format(self):
        """Parse EXIF datetime string with invalid format returns None."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1")
        invalid_exif_datetime = "invalid date format"

        # Act
        parsed_datetime = changer._parse_exif_datetime_string(invalid_exif_datetime)

        # Assert
        assert parsed_datetime is None

    def test_parse_video_datetime_string_utc_format(self):
        """Parse video datetime string with UTC format succeeds."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1")
        utc_datetime = "2023-12-25 14:30:45 UTC"

        # Act
        parsed_datetime = changer._parse_video_datetime_string(utc_datetime)

        # Assert
        assert parsed_datetime is not None
        assert parsed_datetime.year == 2023
        assert parsed_datetime.month == 12
        assert parsed_datetime.day == 25

    def test_parse_video_datetime_string_iso_format(self):
        """Parse video datetime string with ISO format succeeds."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1")
        iso_datetime = "2023-12-25T14:30:45Z"

        # Act
        parsed_datetime = changer._parse_video_datetime_string(iso_datetime)

        # Assert
        assert parsed_datetime is not None
        assert parsed_datetime.year == 2023
        assert parsed_datetime.month == 12
        assert parsed_datetime.day == 25


class TestTimeAdjustmentFunctionality:
    """Test suite for time adjustment functionality."""

    def setup_method(self):
        """Set up test environment for time adjustment tests."""
        self.test_directory = Path(tempfile.mkdtemp())
        # Create a dummy file to satisfy source_path validation
        (self.test_directory / "dummy.jpg").touch()

    def teardown_method(self):
        """Clean up after each test."""
        shutil.rmtree(self.test_directory)

    def test_adjust_timestamps_positive_adjustment(self):
        """Adjust timestamps with positive time delta."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+5d")
        original_timestamps = {
            "DateTime": datetime(2023, 12, 25, 14, 30, 45),
            "DateTimeOriginal": datetime(2023, 12, 25, 14, 30, 45),
            "DateTimeDigitized": None,
        }

        # Act
        adjusted_timestamps = changer.adjust_timestamps(original_timestamps)

        # Assert
        assert adjusted_timestamps["DateTime"] == datetime(2023, 12, 30, 14, 30, 45)
        assert adjusted_timestamps["DateTimeOriginal"] == datetime(
            2023, 12, 30, 14, 30, 45
        )
        assert adjusted_timestamps["DateTimeDigitized"] is None

    def test_adjust_timestamps_negative_adjustment(self):
        """Adjust timestamps with negative time delta."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "-10d")
        original_timestamps = {
            "DateTime": datetime(2023, 12, 25, 14, 30, 45),
            "modification_time": datetime(2023, 12, 25, 16, 0, 0),
        }

        # Act
        adjusted_timestamps = changer.adjust_timestamps(original_timestamps)

        # Assert
        assert adjusted_timestamps["DateTime"] == datetime(2023, 12, 15, 14, 30, 45)
        assert adjusted_timestamps["modification_time"] == datetime(
            2023, 12, 15, 16, 0, 0
        )

    def test_set_file_system_timestamps_uses_modification_time_priority(self):
        """Set file system timestamps prioritizes modification time and makes creation time equal."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1d")
        test_file = self.test_directory / "test_file.txt"
        test_file.write_text("test content")

        target_datetime = datetime(2023, 12, 25, 14, 30, 45)
        timestamps = {
            "modification_time": target_datetime,  # This should be used as primary
            "creation_time": datetime(
                2023, 12, 26, 16, 0, 0
            ),  # Different time, should be ignored
        }

        # Act
        result = changer.set_file_system_timestamps(test_file, timestamps)

        # Assert
        assert result is True

        # Verify both access and modification times are set to modification time
        file_stat = test_file.stat()
        modification_time = datetime.fromtimestamp(file_stat.st_mtime)
        access_time = datetime.fromtimestamp(file_stat.st_atime)

        # Both should be equal to the modification time (within 1 second tolerance)
        assert abs((modification_time - target_datetime).total_seconds()) < 1
        assert abs((access_time - target_datetime).total_seconds()) < 1

    def test_adjust_timestamps_handles_none_values(self):
        """Adjust timestamps handles None values gracefully."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1d")
        original_timestamps = {
            "DateTime": None,
            "DateTimeOriginal": datetime(2023, 12, 25, 14, 30, 45),
            "EmptyField": None,
        }

        # Act
        adjusted_timestamps = changer.adjust_timestamps(original_timestamps)

        # Assert
        assert adjusted_timestamps["DateTime"] is None
        assert adjusted_timestamps["DateTimeOriginal"] == datetime(
            2023, 12, 26, 14, 30, 45
        )
        assert adjusted_timestamps["EmptyField"] is None

    def test_adjust_timestamps_complex_time_delta(self):
        """Adjust timestamps with complex time delta."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1y 2m 3d")
        original_timestamp = datetime(2023, 1, 1, 12, 0, 0)
        original_timestamps = {"test_field": original_timestamp}

        # Act
        adjusted_timestamps = changer.adjust_timestamps(original_timestamps)

        # Assert
        # 1y 2m 3d = 365 + 60 + 3 = 428 days
        expected_timestamp = original_timestamp + timedelta(days=428)
        assert adjusted_timestamps["test_field"] == expected_timestamp

    def test_process_single_file_dry_run_mode(self):
        """Process single file in dry-run mode doesn't modify files."""
        # Arrange
        test_image = self.test_directory / "test_image.jpg"
        test_image.write_bytes(b"fake image data")

        changer = MetadataTimeChanger(str(self.test_directory), "+5d", dry_run=True)

        # Act
        result = changer.process_single_file(test_image)

        # Assert
        assert result["processed"] is True
        assert result["metadata_updated"] is True  # Would be updated in real mode
        assert result["filesystem_updated"] is True  # Would be updated in real mode
        assert "original_timestamps" in result
        assert "adjusted_timestamps" in result
        # Errors are expected when reading metadata from fake image files

    def test_process_single_file_handles_unsupported_format(self):
        """Process single file handles unsupported file formats gracefully."""
        # Arrange
        test_document = self.test_directory / "document.txt"
        test_document.write_text("test document content")

        changer = MetadataTimeChanger(str(self.test_directory), "+5d", dry_run=True)

        # Act
        result = changer.process_single_file(test_document)

        # Assert
        assert result["processed"] is True
        # Should still have filesystem timestamps
        assert "filesystem" in result["original_timestamps"]
        # Should not have metadata timestamps for unsupported format
        assert result["original_timestamps"]["metadata"] == {}


class TestVideoMetadataFunctionality:
    """Test suite for video metadata functionality."""

    def setup_method(self):
        """Set up test environment for video metadata tests."""
        self.test_directory = Path(tempfile.mkdtemp())
        # Create a dummy file to satisfy source_path validation
        (self.test_directory / "dummy.jpg").touch()

    def teardown_method(self):
        """Clean up after each test."""
        shutil.rmtree(self.test_directory)

    def test_write_video_metadata_timestamps_requires_ffmpeg(self):
        """Write video metadata timestamps requires ffmpeg binary."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1d")
        test_video = self.test_directory / "test_video.mp4"
        test_video.write_bytes(b"fake video data")

        timestamps = {
            "creation_time": datetime(2023, 12, 25, 14, 30, 45),
            "encoded_date": datetime(2023, 12, 25, 14, 30, 45),
        }

        # Act
        result = changer.write_video_metadata_timestamps(test_video, timestamps)

        # Assert
        assert result is False
        # Should have an error about ffmpeg (either missing python module or binary)
        assert len(changer.errors) >= 1
        error_message = changer.errors[0].lower()
        assert "ffmpeg" in error_message

    def test_process_video_file_updates_filesystem_only(self):
        """Process video file updates filesystem timestamps but not metadata."""
        # Arrange
        test_video = self.test_directory / "test_video.mp4"
        test_video.write_bytes(b"fake video data")

        changer = MetadataTimeChanger(str(self.test_directory), "+5d", dry_run=True)

        # Act
        result = changer.process_single_file(test_video)

        # Assert
        assert result["processed"] is True
        assert result["filesystem_updated"] is True  # Should update filesystem
        # metadata_updated depends on whether video has readable metadata
        assert "original_timestamps" in result
        assert "adjusted_timestamps" in result


class TestIntegrationFunctionality:
    """Test suite for integration functionality."""

    def setup_method(self):
        """Set up test environment for integration tests."""
        self.test_directory = Path(tempfile.mkdtemp())
        self.setup_mixed_media_files()

    def teardown_method(self):
        """Clean up after each test."""
        shutil.rmtree(self.test_directory)

    def setup_mixed_media_files(self):
        """Create test files with mixed media types."""
        # Create subdirectories
        (self.test_directory / "photos").mkdir()
        (self.test_directory / "videos").mkdir()
        (self.test_directory / "documents").mkdir()

        # Create test files
        (self.test_directory / "photos" / "image1.jpg").write_bytes(b"fake image 1")
        (self.test_directory / "photos" / "image2.png").write_bytes(b"fake image 2")
        (self.test_directory / "videos" / "video1.mp4").write_bytes(b"fake video 1")
        (self.test_directory / "videos" / "video2.avi").write_bytes(b"fake video 2")
        (self.test_directory / "documents" / "doc1.txt").write_text("fake document")

    def test_process_mixed_media_directory_dry_run(self):
        """Process directory with mixed media types in dry-run mode."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+10d", dry_run=True)

        # Act
        media_files = changer.find_media_files()

        # Process all files
        results = []
        for file_path in media_files:
            result = changer.process_single_file(file_path)
            results.append(result)

        # Assert
        assert len(media_files) == 4  # 2 images + 2 videos, no documents
        assert all(result["processed"] for result in results)
        assert all(
            result["filesystem_updated"] for result in results
        )  # All should update filesystem

        # Check file types are correctly identified
        image_files = [
            f for f in media_files if f.suffix.lower() in changer.IMAGE_EXTENSIONS
        ]
        video_files = [
            f for f in media_files if f.suffix.lower() in changer.VIDEO_EXTENSIONS
        ]

        assert len(image_files) == 2
        assert len(video_files) == 2

    def test_time_adjustment_consistency_across_file_types(self):
        """Time adjustment is consistent across different file types."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1y 6m", dry_run=True)
        expected_days = 365 + 180  # 1 year + 6 months

        # Act
        media_files = changer.find_media_files()

        # Process and collect filesystem timestamp adjustments
        adjustment_deltas = []
        for file_path in media_files:
            result = changer.process_single_file(file_path)

            original_mtime = result["original_timestamps"]["filesystem"][
                "modification_time"
            ]
            adjusted_mtime = result["adjusted_timestamps"]["filesystem"][
                "modification_time"
            ]

            delta = adjusted_mtime - original_mtime
            adjustment_deltas.append(delta.days)

        # Assert
        assert len(adjustment_deltas) == 4
        assert all(delta == expected_days for delta in adjustment_deltas)


class TestRIFFPreservingAVIFunctionality:
    """Test suite for RIFF-preserving AVI metadata functionality."""

    def setup_method(self):
        """Set up test environment for RIFF AVI tests."""
        self.test_directory = Path(tempfile.mkdtemp())
        # Create a dummy file to satisfy source_path validation
        (self.test_directory / "dummy.jpg").touch()
        self.setup_test_avi_files()

    def teardown_method(self):
        """Clean up after each test."""
        shutil.rmtree(self.test_directory)

    def setup_test_avi_files(self):
        """Create test AVI files with simulated IDIT chunks."""
        # Create a minimal AVI file structure with IDIT chunk
        # RIFF header + AVI header + minimal IDIT chunk
        riff_header = b"RIFF"
        file_size = struct.pack("<L", 1000)  # Dummy file size
        avi_header = b"AVI "

        # Minimal LIST chunk with IDIT
        list_chunk = b"LIST"
        list_size = struct.pack("<L", 50)  # List chunk size
        info_header = b"INFO"

        # IDIT chunk with test date
        idit_chunk = b"IDIT"
        idit_size = struct.pack("<L", 26)  # 26 bytes for date string
        test_date = b"MON AUG 28 14:14:28 2006\x00\x00"  # Null-terminated, padded

        # Assemble the minimal AVI file
        avi_content = (
            riff_header
            + file_size
            + avi_header
            + list_chunk
            + list_size
            + info_header
            + idit_chunk
            + idit_size
            + test_date
        )

        # Create test AVI files
        test_avi_with_idit = self.test_directory / "test_with_idit.avi"
        test_avi_with_idit.write_bytes(avi_content)

        # Create AVI file without IDIT chunk
        avi_content_no_idit = riff_header + file_size + avi_header + b"dummy data"
        test_avi_without_idit = self.test_directory / "test_without_idit.avi"
        test_avi_without_idit.write_bytes(avi_content_no_idit)

    def test_find_idit_chunk_success(self):
        """Find IDIT chunk in AVI file with valid IDIT chunk."""
        # Arrange
        from avi_riff_date_fixer import find_idit_chunk

        test_avi = self.test_directory / "test_with_idit.avi"
        data = test_avi.read_bytes()

        # Act
        idit_pos, date_data = find_idit_chunk(data)

        # Assert
        assert idit_pos is not None
        assert date_data is not None
        assert b"MON AUG 28 14:14:28 2006" in date_data

    def test_find_idit_chunk_not_found(self):
        """Find IDIT chunk returns None when chunk is not present."""
        # Arrange
        from avi_riff_date_fixer import find_idit_chunk

        test_avi = self.test_directory / "test_without_idit.avi"
        data = test_avi.read_bytes()

        # Act
        idit_pos, date_data = find_idit_chunk(data)

        # Assert
        assert idit_pos is None
        assert date_data is None

    def test_parse_canon_date_valid_format(self):
        """Parse Canon date format successfully."""
        # Arrange
        from avi_riff_date_fixer import parse_canon_date

        canon_date_string = "MON AUG 28 14:14:28 2006"

        # Act
        parsed_date = parse_canon_date(canon_date_string)

        # Assert
        assert parsed_date is not None
        assert parsed_date.year == 2006
        assert parsed_date.month == 8
        assert parsed_date.day == 28
        assert parsed_date.hour == 14
        assert parsed_date.minute == 14
        assert parsed_date.second == 28

    def test_parse_canon_date_with_null_bytes(self):
        """Parse Canon date format with null bytes and whitespace."""
        # Arrange
        from avi_riff_date_fixer import parse_canon_date

        canon_date_string = "MON AUG 28 14:14:28 2006\x00\x00  "

        # Act
        parsed_date = parse_canon_date(canon_date_string)

        # Assert
        assert parsed_date is not None
        assert parsed_date.year == 2006

    def test_parse_canon_date_invalid_format(self):
        """Parse Canon date format with invalid format returns None."""
        # Arrange
        from avi_riff_date_fixer import parse_canon_date

        invalid_date_string = "invalid date format"

        # Act
        parsed_date = parse_canon_date(invalid_date_string)

        # Assert
        assert parsed_date is None

    def test_format_canon_date(self):
        """Format datetime to Canon date format."""
        # Arrange
        from avi_riff_date_fixer import format_canon_date

        test_datetime = datetime(2006, 8, 31, 14, 14, 28)

        # Act
        formatted_date = format_canon_date(test_datetime)

        # Assert
        assert formatted_date == "THU AUG 31 14:14:28 2006"

    def test_fix_avi_date_inplace_success(self):
        """Fix AVI date in place successfully modifies IDIT chunk."""
        # Arrange
        from avi_riff_date_fixer import fix_avi_date_inplace

        test_avi = self.test_directory / "test_with_idit.avi"
        time_delta = timedelta(days=3)

        # Act
        result = fix_avi_date_inplace(test_avi, time_delta)

        # Assert
        assert result is True

        # Verify the date was actually changed
        from avi_riff_date_fixer import find_idit_chunk

        modified_data = test_avi.read_bytes()
        _, date_data = find_idit_chunk(modified_data)

        assert b"THU AUG 31 14:14:28 2006" in date_data

    def test_fix_avi_date_inplace_no_idit_chunk(self):
        """Fix AVI date in place fails gracefully when no IDIT chunk present."""
        # Arrange
        from avi_riff_date_fixer import fix_avi_date_inplace

        test_avi = self.test_directory / "test_without_idit.avi"
        time_delta = timedelta(days=1)

        # Act
        result = fix_avi_date_inplace(test_avi, time_delta)

        # Assert
        assert result is False

    def test_fix_avi_date_inplace_creates_backup(self):
        """Fix AVI date in place creates and cleans up backup file properly."""
        # Arrange
        from avi_riff_date_fixer import fix_avi_date_inplace

        test_avi = self.test_directory / "test_with_idit.avi"
        original_content = test_avi.read_bytes()
        time_delta = timedelta(days=1)

        # Test successful case first
        result_success = fix_avi_date_inplace(test_avi, time_delta)
        backup_path = test_avi.with_suffix(".backup.avi")

        # Assert successful case
        assert result_success is True
        assert not backup_path.exists()  # Backup should be cleaned up after success

        # Reset file for failure test
        test_avi.write_bytes(original_content)

        # Now test failure case - use a file without IDIT chunk
        test_avi_no_idit = self.test_directory / "test_without_idit.avi"
        result_failure = fix_avi_date_inplace(test_avi_no_idit, time_delta)
        backup_path_failure = test_avi_no_idit.with_suffix(".backup.avi")

        # Assert failure case
        assert result_failure is False
        assert (
            not backup_path_failure.exists()
        )  # Backup should be cleaned up after failure too

    def test_metadata_time_changer_integration_with_riff_preserving(self):
        """MetadataTimeChanger integrates RIFF-preserving AVI functionality correctly."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+2d", dry_run=False)
        test_avi = self.test_directory / "test_with_idit.avi"

        # Act
        result = changer.write_avi_metadata_safe_inplace_modify(
            test_avi, datetime(2006, 8, 30, 14, 14, 28)
        )

        # Assert
        assert result is True

        # Verify the date was actually changed
        modified_data = test_avi.read_bytes()
        idit_pos, date_data = changer._find_idit_chunk(modified_data)

        assert idit_pos is not None
        assert b"WED AUG 30 14:14:28 2006" in date_data

    def test_metadata_time_changer_helper_methods(self):
        """MetadataTimeChanger helper methods work correctly."""
        # Arrange
        changer = MetadataTimeChanger(str(self.test_directory), "+1d")

        # Test _parse_canon_date
        parsed_date = changer._parse_canon_date("MON AUG 28 14:14:28 2006")
        assert parsed_date == datetime(2006, 8, 28, 14, 14, 28)

        # Test _format_canon_date
        formatted_date = changer._format_canon_date(datetime(2006, 8, 30, 14, 14, 28))
        assert formatted_date == "WED AUG 30 14:14:28 2006"

        # Test _find_idit_chunk
        test_avi = self.test_directory / "test_with_idit.avi"
        data = test_avi.read_bytes()
        idit_pos, date_data = changer._find_idit_chunk(data)

        assert idit_pos is not None
        assert date_data is not None
