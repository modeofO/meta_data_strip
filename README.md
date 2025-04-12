# Metadata Stripper

A simple GUI application to strip metadata from images and videos.

## Features

- Clean, tabbed interface for processing files and viewing history
- Process individual files or entire folders at once
- Supports common image formats (JPG, PNG, TIFF, GIF, BMP)
- Supports video formats (MP4, MOV, AVI, MKV) with FFmpeg
- File overwrite protection with customizable options
- Remembers your settings between sessions
- Tracks processing history with detailed logs

## Requirements

- Python 3.6+
- Pillow and piexif libraries
- FFmpeg (for video processing)

## Quick Start

1. Install dependencies:
   ```bash
   pip install pillow piexif
   ```

2. Install FFmpeg ([download here](https://ffmpeg.org/download.html))
   - Windows: Add to PATH
   - Mac: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg`

3. Run the application:
   ```bash
   python meta_data_strip.py
   ```

4. Select files/folders, choose output directory, and click "Strip Metadata"

## Key Options

- **Allow overwriting**: Replace original files instead of creating copies
- **Keep history log**: Track all processed files with timestamps and results
- **Don't show again**: Suppress warning dialogs you don't need to see

## Notes

- By default, original files are preserved and clean copies are created with "_clean" suffix
- The application remembers your last used directory and settings
- History tab allows copying file paths and opening locations via right-click menu
- Settings and history are stored locally in preferences.json and processing_history.json 