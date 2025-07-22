# Image and Video Tools

[![CI](https://github.com/woodgoblin/image-tools/workflows/CI/badge.svg)](https://github.com/woodgoblin/image-tools/actions)
[![codecov](https://codecov.io/gh/woodgoblin/image-tools/branch/main/graph/badge.svg)](https://codecov.io/gh/woodgoblin/image-tools)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

Personal Python scripts for organizing photos/videos and tweaking their metadata timestamps.

## ⚠️ Please backup your files first!

These tools modify file metadata and filesystem timestamps. I strongly recommend creating backups before using them, especially if you're working with important media files.

## What's in here

### `image_organizer.py`
Sorts your photos and videos into folders by date (like `2024_01_15/`). It reads EXIF data from photos and metadata from videos to figure out when they were taken.

### `metadata_time_changer.py`
Adjusts timestamps in your files. Useful when your camera's clock was wrong and you want to fix all the dates. Works on both metadata and file timestamps.

### `avi_metadata_analyzer.py`
Diagnostic tool that shows all the date fields in an AVI file. Helpful for debugging when Windows File Explorer shows weird dates.

### `avi_riff_utils.py`
Shared code for handling AVI files properly without corrupting them.

## Installation

```bash
git clone <this-repo>
cd image-tools

# Virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt
```

## How to use

### Organizing files by date
```bash
# Creates an 'organized' folder with date-based subdirectories
python image_organizer.py /path/to/your/photos

# Or specify where to put the organized files
python image_organizer.py /path/to/source --destination /path/to/organized
```

**Output structure:**
```
organized/
├── 2024_01_15/
│   ├── IMG_001.jpg
│   └── IMG_002.jpg
└── 2024_01_16/
    └── VIDEO_001.mp4
```

### Metadata Time Changer

**⚠️ ALWAYS BACKUP FILES FIRST**

```bash
# ALWAYS try dry-run first to see what would happen
python metadata_time_changer.py /path/to/files "+1d" --dry-run

# If it looks good, remove --dry-run to actually change the files
python metadata_time_changer.py /path/to/files "+1d"

# Some examples:
python metadata_time_changer.py /path/to/files "+5d"        # Add 5 days
python metadata_time_changer.py /path/to/files "-2w"        # Subtract 2 weeks  
python metadata_time_changer.py /path/to/files "+1y 2m 3d"  # Add 1 year, 2 months, 3 days
```

### Analyzing AVI files
```bash
# Shows all date fields Windows might be reading
python avi_metadata_analyzer.py video.avi
```

## File formats supported

**Images:** JPG, PNG, TIFF, BMP, GIF, WEBP  
**Videos:** MP4, MOV, AVI, MKV, WMV, FLV, WEBM, M4V

**Note about AVI files:** These are tricky because Windows File Explorer reads dates from specific places in the file. The tools here try to handle this properly, but AVI is a messy format.

## Testing

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=. --cov-report=html
```

## Some technical notes

- The organizer uses file hashes to detect duplicates
- For photos, it reads EXIF DateTimeOriginal, DateTime, DateTimeDigitized
- For videos, it tries various metadata fields depending on the format
- AVI files get special treatment to keep Windows File Explorer happy
- File modification times are synced with creation times for consistency

## Development

Code formatting:
```bash
black .
isort .
```

The CI runs these checks plus all tests on Python 3.9-3.13.

## Dependencies

Main ones: Pillow, pymediainfo, piexif, av, mutagen. See `requirements.txt` for the full list.

## License

See LICENSE file.

---

**Remember: backup your files before running these tools!**
