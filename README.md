# Image and Video Organizer

[![CI](https://github.com/username/image-tools/workflows/CI/badge.svg)](https://github.com/username/image-tools/actions)
[![codecov](https://codecov.io/gh/username/image-tools/branch/main/graph/badge.svg)](https://codecov.io/gh/username/image-tools)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python script that recursively organizes images and videos by their creation date, handles duplicates, and resolves naming conflicts.

## Features

- **Recursive Processing**: Scans all subdirectories for supported media files
- **Date-based Organization**: Sorts files into folders named `YYYY_MM_DD` based on creation date
- **Metadata Extraction**: Uses EXIF data for images and metadata for videos, with filesystem fallback
- **Duplicate Detection**: Hash-based deduplication to avoid copying identical files
- **Conflict Resolution**: Automatically resolves naming conflicts by appending numbers
- **Comprehensive Format Support**: 
  - Images: JPG, JPEG, PNG, TIFF, TIF, BMP, GIF, WEBP
  - Videos: MP4, MOV, AVI, MKV, WMV, FLV, WEBM, M4V

## Installation

1. Clone this repository:
```bash
git clone <repository_url>
cd image-tools
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage
```bash
python image_organizer.py /path/to/your/media/files
```

This will create an `organized` folder in the source directory with files sorted by date.

### Custom Destination
```bash
python image_organizer.py /path/to/source --destination /path/to/destination
```

### Examples

```bash
# Organize photos from a camera card
python image_organizer.py "D:\DCIM\Camera" --destination "C:\Photos\Organized"

# Organize mixed media files
python image_organizer.py "C:\Users\John\Downloads" 
```

## How It Works

1. **Discovery**: Recursively finds all supported image and video files
2. **Date Extraction**: Attempts to extract creation date from:
   - Image EXIF data (DateTimeOriginal, DateTime, DateTimeDigitized)
   - Video metadata (recorded_date, tagged_date, encoded_date)
   - File system timestamps (as fallback)
3. **Organization**: Creates folders named `YYYY_MM_DD` for each unique date
4. **Deduplication**: Calculates SHA-256 hashes to identify and skip duplicate files
5. **Conflict Resolution**: Appends `_001`, `_002`, etc. for files with same name but different content

## Output Example

```
source_folder/
├── IMG_001.jpg (2024-01-15)
├── IMG_002.jpg (2024-01-15) 
├── VIDEO_001.mp4 (2024-01-16)
└── organized/
    ├── 2024_01_15/
    │   ├── IMG_001.jpg
    │   └── IMG_002.jpg
    └── 2024_01_16/
        └── VIDEO_001.mp4
```

## Testing

Run the test suite:
```bash
python -m pytest test_image_organizer.py -v
```

Run tests with coverage:
```bash
python -m pytest test_image_organizer.py -v --cov=image_organizer --cov-report=html
```

## Development

### Code Quality Tools

This project uses several tools to maintain code quality:

#### Format code with Black:
```bash
black .
```

#### Sort imports with isort:
```bash
isort .
```

#### Lint with flake8:
```bash
flake8 .
```

#### Run all quality checks (same as CI):
```bash
black --check --diff .
isort --check-only --diff .
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
pytest test_image_organizer.py -v --cov=image_organizer --cov-report=xml
```

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt
```

## Dependencies

- **Pillow**: Image processing and EXIF data extraction
- **exifread**: Alternative EXIF data extraction
- **pymediainfo**: Video metadata extraction
- **pytest**: Testing framework

## Error Handling

The script handles various error conditions gracefully:
- Missing or corrupted metadata
- Unreadable files
- Permission errors
- Invalid file formats

Any errors encountered during processing are reported in the final statistics without stopping the entire operation.

## License

See LICENSE file for details.
