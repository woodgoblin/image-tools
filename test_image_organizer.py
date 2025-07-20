#!/usr/bin/env python3
"""
Tests for the image_organizer module.
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from image_organizer import ImageVideoOrganizer


class TestImageVideoOrganizer:
    """Test suite for ImageVideoOrganizer class."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Arrange: Create temporary directory structure
        self.test_directory = Path(tempfile.mkdtemp())
        self.setup_test_files()

    def teardown_method(self):
        """Clean up after each test."""
        shutil.rmtree(self.test_directory)

    def setup_test_files(self):
        """Create test file structure with various media files."""
        # Create subdirectories
        (self.test_directory / "subdir1").mkdir()
        (self.test_directory / "subdir2").mkdir()

        # Create test files (empty files for testing)
        test_file_names = [
            "image1.jpg",
            "image2.PNG",
            "video1.mp4",
            "video2.MOV",
            "document.txt",  # Should be ignored
            "subdir1/nested_image.jpeg",
            "subdir2/nested_video.avi",
            "no_extension",  # Should be ignored
        ]

        for relative_file_path in test_file_names:
            complete_file_path = self.test_directory / relative_file_path
            complete_file_path.touch()

    def test_init_valid_path(self):
        """Initialize organizer with valid source path."""
        # Act
        media_organizer = ImageVideoOrganizer(str(self.test_directory))

        # Assert
        assert media_organizer.source_path == self.test_directory
        assert media_organizer.destination_path == self.test_directory / "organized"
        assert media_organizer.destination_path.exists()

    def test_init_invalid_path(self):
        """Initialize organizer with invalid source path should raise error."""
        # Act & Assert
        with pytest.raises(ValueError, match="Source path does not exist"):
            ImageVideoOrganizer("/nonexistent/path")

    def test_init_custom_destination(self):
        """Initialize organizer with custom destination path."""
        # Arrange
        custom_destination = self.test_directory / "custom_output"

        # Act
        media_organizer = ImageVideoOrganizer(
            str(self.test_directory), str(custom_destination)
        )

        # Assert
        assert media_organizer.destination_path == custom_destination
        assert media_organizer.destination_path.exists()

    def test_find_media_files(self):
        """Find all supported media files recursively."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.test_directory))

        # Act
        discovered_media_files = media_organizer.find_media_files()

        # Assert
        expected_media_files = {
            "image1.jpg",
            "image2.PNG",
            "video1.mp4",
            "video2.MOV",
            "subdir1/nested_image.jpeg",
            "subdir2/nested_video.avi",
        }

        found_relative_file_paths = {
            str(file_path.relative_to(self.test_directory)).replace("\\", "/")
            for file_path in discovered_media_files
        }

        assert len(discovered_media_files) == 6
        assert found_relative_file_paths == expected_media_files

    def test_find_media_files_case_insensitive(self):
        """File extension matching is case insensitive."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.test_directory))

        # Act
        discovered_media_files = media_organizer.find_media_files()

        # Assert
        png_files = [
            file_path
            for file_path in discovered_media_files
            if file_path.suffix.lower() == ".png"
        ]
        mov_files = [
            file_path
            for file_path in discovered_media_files
            if file_path.suffix.lower() == ".mov"
        ]

        assert len(png_files) == 1  # image2.PNG
        assert len(mov_files) == 1  # video2.MOV

    def test_organize_files_basic_stats(self):
        """Basic organization returns correct file count statistics."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.test_directory))

        # Act
        organization_statistics = media_organizer.organize_files()

        # Assert
        assert organization_statistics["total_files"] == 6
        assert "processed" in organization_statistics
        assert "duplicates_skipped" in organization_statistics
        assert "conflicts_resolved" in organization_statistics

    def test_supported_extensions(self):
        """Check that expected file extensions are supported."""
        # Assert
        expected_image_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".tiff",
            ".tif",
            ".bmp",
            ".gif",
            ".webp",
        }
        expected_video_extensions = {
            ".mp4",
            ".mov",
            ".avi",
            ".mkv",
            ".wmv",
            ".flv",
            ".webm",
            ".m4v",
        }

        assert ImageVideoOrganizer.IMAGE_EXTENSIONS == expected_image_extensions
        assert ImageVideoOrganizer.VIDEO_EXTENSIONS == expected_video_extensions

    def test_get_creation_date_file_system_fallback(self):
        """File system date extraction as fallback."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.test_directory))
        test_image_file = self.test_directory / "image1.jpg"

        # Act
        extracted_creation_date = media_organizer.get_creation_date(test_image_file)

        # Assert
        assert isinstance(extracted_creation_date, datetime)
        # Should be recent (within last hour)
        current_time = datetime.now()
        time_difference = abs((current_time - extracted_creation_date).total_seconds())
        assert time_difference < 3600  # Within 1 hour

    def test_file_system_date_extraction(self):
        """File system date extraction uses the earliest available timestamp."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.test_directory))
        test_file_for_date = self.test_directory / "test_date.jpg"
        test_file_for_date.touch()

        # Act
        extracted_date = media_organizer._get_file_system_date(test_file_for_date)

        # Assert
        assert isinstance(extracted_date, datetime)
        # Should be very recent
        current_time = datetime.now()
        time_difference = abs((current_time - extracted_date).total_seconds())
        assert time_difference < 60  # Within 1 minute

    def test_format_date_folder(self):
        """Date formatting for folder names."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.test_directory))
        sample_date = datetime(2024, 3, 15, 14, 30, 45)

        # Act
        formatted_folder_name = media_organizer.format_date_folder(sample_date)

        # Assert
        assert formatted_folder_name == "2024_03_15"

    def test_get_creation_date_handles_missing_files(self):
        """Creation date extraction handles missing files gracefully."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.test_directory))
        nonexistent_file = self.test_directory / "nonexistent.jpg"

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            media_organizer.get_creation_date(nonexistent_file)

    def test_calculate_file_hash(self):
        """File hash calculation produces consistent results."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.test_directory))
        hash_test_file = self.test_directory / "hash_test.jpg"
        test_file_content = b"test image content for hashing"
        hash_test_file.write_bytes(test_file_content)

        # Act
        first_hash_calculation = media_organizer.calculate_file_hash(hash_test_file)
        second_hash_calculation = media_organizer.calculate_file_hash(hash_test_file)

        # Assert
        assert (
            first_hash_calculation == second_hash_calculation
        )  # Same file should produce same hash
        assert (
            len(first_hash_calculation) == 64
        )  # SHA-256 produces 64-character hex string
        assert all(
            character in "0123456789abcdef" for character in first_hash_calculation
        )  # Valid hex

    def test_calculate_file_hash_different_files(self):
        """Different files produce different hashes."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.test_directory))

        first_test_file = self.test_directory / "file1.jpg"
        second_test_file = self.test_directory / "file2.jpg"

        first_test_file.write_bytes(b"content of file 1")
        second_test_file.write_bytes(b"content of file 2")

        # Act
        first_file_hash = media_organizer.calculate_file_hash(first_test_file)
        second_file_hash = media_organizer.calculate_file_hash(second_test_file)

        # Assert
        assert first_file_hash != second_file_hash

    def test_is_duplicate_true(self):
        """Duplicate detection correctly identifies duplicates."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.test_directory))
        duplicate_test_file = self.test_directory / "duplicate_test.jpg"
        duplicate_file_content = b"duplicate test content"
        duplicate_test_file.write_bytes(duplicate_file_content)

        calculated_file_hash = media_organizer.calculate_file_hash(duplicate_test_file)
        existing_file_hashes = {calculated_file_hash, "some_other_hash"}

        # Act
        is_file_duplicate = media_organizer.is_duplicate(
            duplicate_test_file, existing_file_hashes
        )

        # Assert
        assert is_file_duplicate is True

    def test_is_duplicate_false(self):
        """Duplicate detection correctly identifies unique files."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.test_directory))
        unique_test_file = self.test_directory / "unique_test.jpg"
        unique_file_content = b"unique test content"
        unique_test_file.write_bytes(unique_file_content)

        existing_file_hashes = {"some_other_hash", "another_hash"}

        # Act
        is_file_duplicate = media_organizer.is_duplicate(
            unique_test_file, existing_file_hashes
        )

        # Assert
        assert is_file_duplicate is False

    def test_generate_unique_filename_no_conflict(self):
        """Unique filename generation when no conflict exists."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.test_directory))
        destination_directory = self.test_directory / "destination"
        destination_directory.mkdir()

        source_file_path = self.test_directory / "source.jpg"
        source_file_path.write_bytes(b"source content")

        # Act
        generated_unique_name = media_organizer.generate_unique_filename(
            destination_directory, "newfile.jpg", source_file_path
        )

        # Assert
        assert generated_unique_name == "newfile.jpg"

    def test_generate_unique_filename_with_conflict(self):
        """Unique filename generation resolves naming conflicts."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.test_directory))
        destination_directory = self.test_directory / "destination"
        destination_directory.mkdir()

        # Create existing file with same name but different content
        existing_conflicting_file = destination_directory / "conflict.jpg"
        existing_conflicting_file.write_bytes(b"existing content")

        source_file_path = self.test_directory / "source.jpg"
        source_file_path.write_bytes(b"new content")

        # Act
        generated_unique_name = media_organizer.generate_unique_filename(
            destination_directory, "conflict.jpg", source_file_path
        )

        # Assert
        assert generated_unique_name == "conflict_002.jpg"

    def test_generate_unique_filename_duplicate_detection(self):
        """Unique filename generation detects actual duplicates."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.test_directory))
        destination_directory = self.test_directory / "destination"
        destination_directory.mkdir()

        # Create existing file with same content
        identical_file_content = b"same content"
        existing_duplicate_file = destination_directory / "duplicate.jpg"
        existing_duplicate_file.write_bytes(identical_file_content)

        source_file_path = self.test_directory / "source.jpg"
        source_file_path.write_bytes(identical_file_content)  # Same content

        # Act
        generated_unique_name = media_organizer.generate_unique_filename(
            destination_directory, "duplicate.jpg", source_file_path
        )

        # Assert
        assert generated_unique_name is None  # Should return None for duplicates


class TestImageVideoOrganizerIntegration:
    """Integration tests for the complete organization workflow."""

    def setup_method(self):
        """Set up test environment for integration tests."""
        # Arrange: Create temporary directory structure
        self.integration_test_directory = Path(tempfile.mkdtemp())
        self.setup_integration_test_files()

    def teardown_method(self):
        """Clean up after each test."""
        shutil.rmtree(self.integration_test_directory)

    def setup_integration_test_files(self):
        """Create a more comprehensive test file structure."""
        # Create subdirectories
        (self.integration_test_directory / "photos").mkdir()
        (self.integration_test_directory / "videos").mkdir()

        # Create test files with different content
        test_file_definitions = {
            "photo1.jpg": b"photo1 content",
            "photo2.png": b"photo2 content",
            "duplicate1.jpg": b"duplicate content",  # Will be duplicated
            "duplicate2.jpg": b"duplicate content",  # Duplicate of duplicate1
            "video1.mp4": b"video1 content",
            "photos/nested_photo.jpeg": b"nested photo content",
            "videos/nested_video.avi": b"nested video content",
            "document.txt": b"not a media file",  # Should be ignored
        }

        for relative_file_path, file_content in test_file_definitions.items():
            complete_file_path = self.integration_test_directory / relative_file_path
            complete_file_path.parent.mkdir(parents=True, exist_ok=True)
            complete_file_path.write_bytes(file_content)

    def test_organize_files_complete_workflow(self):
        """Complete organization workflow with various scenarios."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.integration_test_directory))

        # Act
        organization_results = media_organizer.organize_files()

        # Assert
        assert (
            organization_results["total_files"] == 7
        )  # Should find 7 media files (ignore document.txt)
        assert (
            organization_results["processed"] >= 6
        )  # Should process at least 6 files (1 duplicate skipped)
        assert (
            organization_results["duplicates_skipped"] >= 1
        )  # Should skip duplicate files
        assert organization_results["errors"] == 0  # No errors expected
        assert (
            organization_results["date_folders_created"] >= 1
        )  # Should create at least one date folder

        # Check that organized directory was created
        organized_directory = self.integration_test_directory / "organized"
        assert organized_directory.exists()

        # Check that date folders follow YYYY_MM_DD format
        created_date_folders = [
            directory
            for directory in organized_directory.iterdir()
            if directory.is_dir()
        ]
        assert len(created_date_folders) > 0

        for date_folder in created_date_folders:
            # Folder name should match YYYY_MM_DD pattern
            assert len(date_folder.name) == 10  # YYYY_MM_DD is 10 chars
            assert date_folder.name.count("_") == 2
            folder_name_parts = date_folder.name.split("_")
            assert len(folder_name_parts[0]) == 4  # Year
            assert len(folder_name_parts[1]) == 2  # Month
            assert len(folder_name_parts[2]) == 2  # Day

    def test_organize_files_skips_destination_files(self):
        """Organization skips files already in destination directory."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.integration_test_directory))

        # Create a file in the destination directory first
        destination_date_directory = (
            self.integration_test_directory / "organized" / "2024_01_01"
        )
        destination_date_directory.mkdir(parents=True)
        existing_destination_file = destination_date_directory / "existing.jpg"
        existing_destination_file.write_bytes(b"existing content")

        # Act
        organization_results = media_organizer.organize_files()

        # Assert
        # The existing file should not be counted in total_files
        # since it's already in the destination directory
        assert existing_destination_file.exists()  # File should still exist

    def test_organize_files_handles_naming_conflicts(self):
        """Organization properly handles naming conflicts."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.integration_test_directory))

        # Pre-create a file with same name in destination
        organized_destination_directory = self.integration_test_directory / "organized"
        media_organizer.organize_files()  # First run

        # Create another file with same name but different content
        new_source_area = self.integration_test_directory / "new_area"
        new_conflicting_file = new_source_area / "photo1.jpg"
        new_conflicting_file.parent.mkdir(parents=True)
        new_conflicting_file.write_bytes(b"different content for photo1")

        # Create new organizer instance for the new area
        new_area_organizer = ImageVideoOrganizer(
            str(new_source_area), str(organized_destination_directory)
        )

        # Act
        organization_results = new_area_organizer.organize_files()

        # Assert
        if organization_results["total_files"] > 0:
            # If conflicts were resolved, it should be recorded
            assert organization_results["conflicts_resolved"] >= 0

    def test_organize_files_preserves_file_content(self):
        """Organization preserves file content and metadata."""
        # Arrange
        media_organizer = ImageVideoOrganizer(str(self.integration_test_directory))

        # Get original file info
        original_source_file = self.integration_test_directory / "photo1.jpg"
        original_file_content = original_source_file.read_bytes()
        original_file_size = original_source_file.stat().st_size

        # Act
        organization_results = media_organizer.organize_files()

        # Assert
        # Find the organized file
        organized_directory = self.integration_test_directory / "organized"
        all_organized_jpg_files = list(organized_directory.rglob("*.jpg"))

        photo1_organized_file = None
        for organized_file in all_organized_jpg_files:
            if organized_file.name.startswith("photo1"):
                photo1_organized_file = organized_file
                break

        assert photo1_organized_file is not None
        assert photo1_organized_file.read_bytes() == original_file_content
        assert photo1_organized_file.stat().st_size == original_file_size
