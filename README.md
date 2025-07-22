# Image and Video Tools

[![CI](https://github.com/woodgoblin/image-tools/workflows/CI/badge.svg)](https://github.com/woodgoblin/image-tools/actions)
[![codecov](https://codecov.io/gh/woodgoblin/image-tools/branch/main/graph/badge.svg)](https://codecov.io/gh/woodgoblin/image-tools)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

Professional-grade Python tools for organizing and managing image/video metadata with advanced AVI support.

## ⚠️ IMPORTANT DISCLAIMERS

### 🚨 **BACKUP YOUR FILES BEFORE USE**
These tools modify file metadata and timestamps. **ALWAYS create backups** of your media files before running any operations. While the tools include backup mechanisms, data corruption or loss is possible.

### 🎯 **Production-Ready Professional Tools**
These are **professional-grade tools** designed for real-world use, not examples or demos. They include:
- RIFF-preserving AVI metadata modification for Windows File Explorer compatibility
- Comprehensive error handling and backup/restore mechanisms  
- Extensive test coverage (69+ tests)
- Support for all major image and video formats

### 📋 **Recommended Workflow**
1. **Backup your files** to a separate location
2. **Test on a small subset** of files first
3. **Use `--dry-run` mode** to preview changes
4. **Verify results** before processing large batches

---

## 🛠️ Tools Included

### 1. **Image/Video Organizer** (`image_organizer.py`)
Recursively organizes images and videos by creation date with duplicate detection and conflict resolution.

### 2. **Metadata Time Changer** (`metadata_time_changer.py`) 
Adjusts timestamps in image EXIF and video metadata, including Windows-compatible AVI files.

### 3. **AVI RIFF Date Fixer** (`avi_riff_date_fixer.py`)
Specialized tool for AVI files that preserves Windows File Explorer "Media created" compatibility.

### 4. **AVI Metadata Analyzer** (`avi_metadata_analyzer.py`)
Diagnostic tool that shows all possible date fields in AVI files for troubleshooting.

---

## 📦 Installation

```bash
# Clone repository
git clone <repository_url>
cd image-tools

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Dependencies
- **Pillow**: Image processing and EXIF data
- **exifread**: EXIF data extraction
- **pymediainfo**: Video metadata extraction  
- **av**: Professional video metadata handling
- **mutagen**: Audio/video metadata manipulation
- **ffmpeg**: Video processing (binary required)

---

## 🎯 Usage

### Image/Video Organizer

**Organize files by creation date:**
```bash
# Basic usage - creates 'organized' folder
python image_organizer.py /path/to/media/files

# Custom destination
python image_organizer.py /path/to/source --destination /path/to/destination

# Example: Organize camera photos
python image_organizer.py "D:\DCIM\Camera" --destination "C:\Photos\Organized"
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
# DRY RUN (preview changes without modifying files)
python metadata_time_changer.py /path/to/files "+1d" --dry-run

# Add time to metadata and filesystem timestamps
python metadata_time_changer.py /path/to/files "+1y 2m 3d"
python metadata_time_changer.py /path/to/files "+5d"
python metadata_time_changer.py /path/to/files "+2h 30m"

# Subtract time
python metadata_time_changer.py /path/to/files "-1w 2d"

# Process single file
python metadata_time_changer.py /path/to/video.avi "+6m"
```

**Time format examples:**
- `+1d` = Add 1 day
- `-2w` = Subtract 2 weeks  
- `+1y 6m 15d` = Add 1 year, 6 months, 15 days
- `+12h 30m` = Add 12 hours, 30 minutes

### AVI RIFF Date Fixer (Specialized)

**For AVI files requiring Windows File Explorer compatibility:**
```bash
# BACKUP FILES FIRST
python avi_riff_date_fixer.py video.avi "+3d"
python avi_riff_date_fixer.py video.avi "-1w"
```

### AVI Metadata Analyzer (Diagnostic)

**Troubleshoot AVI metadata issues:**
```bash
python avi_metadata_analyzer.py video.avi
```

Shows all metadata fields including Windows File Explorer compatibility.

---

## 🎯 Supported Formats

### Images
JPG, JPEG, PNG, TIFF, TIF, BMP, GIF, WEBP

### Videos  
MP4, MOV, AVI, MKV, WMV, FLV, WEBM, M4V

### Special AVI Support
- **RIFF-preserving modification** maintains Windows File Explorer compatibility
- Preserves "Media created" field in Windows File Properties
- Works with Canon, Sony, and other camera AVI files

---

## 🧪 Testing

**Run all tests:**
```bash
python -m pytest -v
```

**Run with coverage:**
```bash
python -m pytest --cov=. --cov-report=html
```

**Test specific functionality:**
```bash
# Image organizer tests
python -m pytest test_image_organizer.py -v

# Metadata time changer tests  
python -m pytest test_metadata_time_changer.py -v

# RIFF-preserving AVI tests
python -m pytest test_metadata_time_changer.py::TestRIFFPreservingAVIFunctionality -v
```

**Test Coverage: 69+ comprehensive tests covering:**
- Time parsing and adjustment logic
- File discovery and format support
- Metadata reading/writing for all formats
- RIFF-preserving AVI modification
- Error handling and backup/restore
- Integration scenarios

---

## 🏗️ How It Works

### Image/Video Organizer
1. **Discovery**: Recursively finds supported media files
2. **Date Extraction**: EXIF data → Video metadata → Filesystem timestamps
3. **Organization**: Creates `YYYY_MM_DD` folders
4. **Deduplication**: SHA-256 hash comparison
5. **Conflict Resolution**: Automatic filename numbering

### Metadata Time Changer
1. **Parsing**: Flexible time format parsing (`+1y 2m 3d`)
2. **Reading**: Extracts EXIF, video metadata, filesystem timestamps
3. **Adjustment**: Applies time delta to all relevant fields
4. **Writing**: Updates metadata and filesystem timestamps
5. **AVI Special Handling**: RIFF-preserving modification for Windows compatibility

### AVI RIFF-Preserving Technology
- **Direct byte modification** of IDIT chunks
- **Preserves container structure** (unlike FFmpeg remuxing)
- **Maintains Windows compatibility** for "Media created" field
- **Backup/restore mechanism** for safety

---

## 🔧 Development

### Code Quality
```bash
# Format code
black .

# Sort imports  
isort .

# Run quality checks (same as CI)
black --check --diff .
isort --check-only --diff .
python -m pytest -v --cov=. --cov-report=xml
```

### Development Dependencies
```bash
pip install -r requirements-dev.txt
```

---

## 🛡️ Error Handling

- **Graceful degradation**: Continues processing on individual file errors
- **Comprehensive logging**: Detailed error reporting
- **Backup mechanisms**: Automatic backup/restore for metadata operations
- **Validation**: File format and metadata validation
- **Recovery**: Restore from backup on failure

---

## 📚 Technical Details

### Windows File Explorer Compatibility
The AVI tools solve a complex technical challenge: Windows File Explorer reads "Media created" from specific RIFF metadata fields (`mastered_date` from `IDIT` chunks), not standard video metadata. Our RIFF-preserving approach maintains this compatibility.

### Metadata Fields Supported
- **Images**: DateTimeOriginal, DateTime, DateTimeDigitized (EXIF)
- **Videos**: creation_time, encoded_date, tagged_date, recorded_date
- **AVI Special**: IDIT, ICRD chunks (Windows-compatible)
- **Filesystem**: modification_time, creation_time (synchronized)

### Architecture
- **DRY Principle**: Shared helper methods across tools
- **Professional Error Handling**: Backup/restore with comprehensive logging
- **Extensible Design**: Easy to add new formats and metadata fields
- **Test-Driven**: 69+ tests ensure reliability

---

## 📄 License

See LICENSE file for details.

---

## 🤝 Contributing

1. **Backup test files** before development
2. **Run tests** before committing: `python -m pytest -v`
3. **Follow code style**: `black .` and `isort .`
4. **Add tests** for new functionality
5. **Update documentation** for user-facing changes

---

## ⚠️ Final Warning

**These tools modify file metadata and timestamps. Data loss is possible. ALWAYS backup your files before use.**
