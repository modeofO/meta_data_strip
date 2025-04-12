# Metadata Stripper

A simple GUI application to strip metadata from images and videos.

## Features

- Simple and intuitive Tkinter interface
- Support for multiple file selection
- Bulk processing of entire folders
- Progress tracking
- Supports common image formats (JPG, PNG, TIFF, GIF, BMP)
- Supports common video formats (MP4, MOV, AVI, MKV) with FFmpeg
- Preserves original files by creating clean copies

## Requirements

- Python 3.6+
- PIL (Pillow)
- piexif
- FFmpeg (for video processing)

## Installation

1. Clone this repository
2. Install the required Python packages:

```bash
pip install pillow piexif
```

3. Install FFmpeg:
   - **Windows**: 
     - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
     - Extract the files to a location on your system (e.g., `C:\ffmpeg`)
     - Add the `bin` folder to your system PATH:
       - Right-click on "This PC" or "My Computer" and select "Properties"
       - Click on "Advanced system settings"
       - Click the "Environment Variables" button
       - Under "System variables", find the "Path" variable, select it and click "Edit"
       - Click "New" and add the path to the bin folder (e.g., `C:\ffmpeg\bin`)
       - Click "OK" to close all dialogs
   - **Mac**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` or equivalent for your distribution

## Usage

1. Run the application:

```bash
python meta_data_strip.py
```

2. Click "Select Files/Folder" and choose whether you want to select individual files or an entire folder.
3. Set your output directory by clicking the "Browse" button.
4. Click "Strip Metadata" to begin processing.
5. Wait for the process to complete.

## How It Works

- **Images**: The application creates new copies of images without any metadata by using the PIL and piexif libraries.
- **Videos**: FFmpeg is used to create copies of videos with all metadata removed, while preserving the original video and audio quality.

## Troubleshooting Video Processing

If you encounter issues with video processing:

1. **FFmpeg Not Found**: Ensure FFmpeg is properly installed and added to your system PATH.
2. **Video Processing Errors**:
   - The application will automatically try an alternative method for MP4/MOV files if the initial method fails.
   - For large video files, processing can take significant time (there's a 5-minute timeout).
   - Some video formats may have compatibility issues. Try converting your video to MP4 format first.
3. **Large Files**: For very large files, the application may appear unresponsive while processing. This is normal, just wait for it to complete.

## Notes

- The original files are never modified - clean copies are created in your selected output directory.
- For large video files, processing may take some time.
- If FFmpeg is not available, the application will still work for images but will skip video files with a notification. 