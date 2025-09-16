import os
import sys
import argparse
import json
import subprocess
from typing import Any, Dict, List, Union

from PIL import Image
import piexif


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


def is_image_file(path: str) -> bool:
    return os.path.splitext(path.lower())[1] in IMAGE_EXTENSIONS


def is_video_file(path: str) -> bool:
    return os.path.splitext(path.lower())[1] in VIDEO_EXTENSIONS


def _safe_serialize(value: Any) -> Any:
    """Convert EXIF and PIL values to JSON-serializable forms."""
    try:
        # piexif Rational objects
        if hasattr(value, "numerator") and hasattr(value, "denominator"):
            den = value.denominator if value.denominator != 0 else 1
            return value.numerator / den
        # Bytes → try utf-8, else hex
        if isinstance(value, (bytes, bytearray)):
            try:
                return value.decode("utf-8", errors="replace").strip("\x00")
            except Exception:
                return value.hex()
        # Tuples of rationals or nested values
        if isinstance(value, (list, tuple)):
            return [_safe_serialize(v) for v in value]
        # Dicts
        if isinstance(value, dict):
            return {str(k): _safe_serialize(v) for k, v in value.items()}
        # Primitive
        return value
    except Exception:
        # Fallback to string representation
        return str(value)


def _extract_exif_dict(image: Image.Image, file_path: str) -> Dict[str, Dict[str, Any]]:
    """Extract EXIF using piexif and map tag IDs to human-readable names."""
    exif_data: Dict[str, Dict[str, Any]] = {}

    # Try to load EXIF from file path first (more reliable for some images)
    try:
        exif_dict = piexif.load(file_path)
    except Exception:
        # Fallback to EXIF bytes in the image info
        try:
            exif_bytes = image.info.get("exif", b"")
            exif_dict = piexif.load(exif_bytes)
        except Exception:
            return {}

    for ifd_name in ("0th", "Exif", "GPS", "1st", "Interop"):
        tagged: Dict[str, Any] = {}
        if ifd_name not in exif_dict:
            continue
        for tag_id, raw_value in exif_dict.get(ifd_name, {}).items():
            tag_info = piexif.TAGS.get(ifd_name, {}).get(tag_id)
            tag_name = tag_info["name"] if tag_info and "name" in tag_info else str(tag_id)
            tagged[tag_name] = _safe_serialize(raw_value)
        if tagged:
            exif_data[ifd_name] = tagged

    return exif_data


def extract_image_metadata(path: str) -> Dict[str, Any]:
    meta: Dict[str, Any] = {"path": path, "type": "image"}
    with Image.open(path) as img:
        meta["format"] = img.format
        meta["mode"] = img.mode
        meta["size"] = {"width": img.width, "height": img.height}

        # PIL image.info may contain metadata for PNG/GIF/etc.
        if img.info:
            meta["info"] = {str(k): _safe_serialize(v) for k, v in img.info.items()}

        # EXIF for JPEG/TIFF
        ext = os.path.splitext(path.lower())[1]
        if ext in {".jpg", ".jpeg", ".tiff"}:
            exif = _extract_exif_dict(img, path)
            if exif:
                meta["exif"] = exif

    return meta


def ffprobe_available() -> bool:
    try:
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return True
    except Exception:
        return False


def extract_video_metadata(path: str) -> Dict[str, Any]:
    meta: Dict[str, Any] = {"path": path, "type": "video"}
    if not ffprobe_available():
        meta["warning"] = "ffprobe not found in PATH; video metadata unavailable"
        return meta

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-print_format",
        "json",
        path,
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, timeout=60)
        if result.returncode != 0:
            meta["error"] = result.stderr.strip()
            return meta
        data = json.loads(result.stdout or "{}")
        # Keep format and streams as-is; they are already JSON-friendly
        meta.update({
            "format": data.get("format"),
            "streams": data.get("streams"),
        })
        return meta
    except subprocess.TimeoutExpired:
        meta["error"] = "ffprobe timed out"
        return meta
    except Exception as exc:
        meta["error"] = str(exc)
        return meta


def iter_input_paths(paths: List[str], recursive: bool) -> List[str]:
    collected: List[str] = []
    for p in paths:
        if not os.path.exists(p):
            continue
        if os.path.isdir(p):
            if recursive:
                for root, _, files in os.walk(p):
                    for name in files:
                        collected.append(os.path.join(root, name))
            else:
                # Only immediate files in the directory (non-recursive)
                for name in os.listdir(p):
                    full = os.path.join(p, name)
                    if os.path.isfile(full):
                        collected.append(full)
        else:
            collected.append(p)
    return collected


def main(argv: Union[List[str], None] = None) -> int:
    parser = argparse.ArgumentParser(description="Print image/video metadata to stdout (no modifications).")
    parser.add_argument("paths", nargs="+", help="Files and/or directories to inspect")
    parser.add_argument("-r", "--recursive", action="store_true", help="Recurse into directories")
    args = parser.parse_args(argv)

    inputs = iter_input_paths(args.paths, args.recursive)
    if not inputs:
        print("No valid inputs found.")
        return 1

    results: List[Dict[str, Any]] = []
    for path in inputs:
        ext = os.path.splitext(path.lower())[1]
        try:
            if is_image_file(path):
                results.append(extract_image_metadata(path))
            elif is_video_file(path):
                results.append(extract_video_metadata(path))
            else:
                results.append({
                    "path": path,
                    "type": "unknown",
                    "note": f"Unsupported file extension: {ext}",
                })
        except Exception as exc:
            results.append({
                "path": path,
                "type": "error",
                "error": str(exc),
            })

    # Print as JSON array for easy consumption
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())


