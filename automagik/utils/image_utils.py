"""Utility functions for image handling (download, metadata extraction).

These helpers centralise common image-processing tasks such as:
1. Streaming-download of an image to a temporary file.
2. Extraction of binary metadata (format, dimensions, EXIF, SHA-256, etc.).
3. A convenience wrapper that fetches an image from a URL and returns both the
   filesystem path, mime-type and metadata in a single call.

NOTE: The functions are completely self-contained and make **no** assumptions
about higher-level frameworks. They can therefore be safely reused by agents,
API controllers or background tasks.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

import requests

# ---------------------------------------------------------------------------
# Optional dependency – Pillow is required only for EXIF/metadata extraction.
# We attempt to import it lazily so that environments without Pillow can still
# use the basic *download_image* utility.
# ---------------------------------------------------------------------------
try:
    from PIL import Image, ExifTags  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – handled gracefully
    Image = None  # type: ignore
    ExifTags = None  # type: ignore

__all__ = [
    "download_image",
    "get_image_metadata",
    "fetch_image_with_metadata",
]


def download_image(
    url: str,
    tmp_dir: Optional[str | os.PathLike[str]] = None,
    *,
    timeout: int = 10,
) -> Tuple[Path, str]:
    """Stream-download an image and persist it to a temporary file.

    Parameters
    ----------
    url : str
        Absolute URL of the image to download.
    tmp_dir : str | os.PathLike | None
        Optional directory in which the temporary file should be created. If
        *None* a system-defined temp directory is used.
    timeout : int, default 10
        HTTP timeout in seconds.

    Returns
    -------
    (path, mime_type) : Tuple[pathlib.Path, str]
        *path* is the **absolute** file path of the saved image.
        *mime_type* is the MIME-type reported by the remote server. If the
        server does not return a *Content-Type* header, the generic
        ``application/octet-stream`` value is used.
    """
    resp = requests.get(url, stream=True, timeout=timeout)
    resp.raise_for_status()

    # Extract MIME type (ignore charset, etc.)
    mime = resp.headers.get("content-type", "application/octet-stream").split(";")[0]

    # Map recognised MIME types to appropriate file extensions – fallback to
    # generic *.bin* when unknown so that the file always has an extension.
    ext = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
        "image/tiff": ".tiff",
        "image/heic": ".heic",
    }.get(mime, ".bin")

    tmp_dir = Path(tmp_dir) if tmp_dir else Path(tempfile.gettempdir())
    tmp_dir.mkdir(parents=True, exist_ok=True)

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=tmp_dir)
    with tmp_file as f:
        shutil.copyfileobj(resp.raw, f)

    return Path(tmp_file.name).resolve(), mime


def _safe_exif(img):  # type: ignore
    """Return *decoded* EXIF data if available – swallow errors otherwise.

    The function is resilient to environments where *Pillow* is not available
    (in which case it simply returns an empty dictionary).
    """
    if Image is None or ExifTags is None:
        # Pillow not installed – EXIF extraction not possible.
        return {}

    if not hasattr(img, "_getexif") or img._getexif() is None:  # type: ignore[attr-defined]
        return {}
    exif_raw = img._getexif()  # type: ignore[attr-defined]
    decoded: Dict[str, Any] = {}
    for tag, value in exif_raw.items():
        decoded[ExifTags.TAGS.get(tag, tag)] = value  # type: ignore[index]
    return decoded


def get_image_metadata(path: str | os.PathLike[str]) -> Dict[str, Any]:
    """Extract useful metadata from an image using *Pillow*.

    Returns a dictionary such as::

        {
            "format": "JPEG",
            "mode": "RGB",
            "width": 1920,
            "height": 1080,
            "bytes": 254763,
            "sha256": "ab12…",
            "exif": {...}
        }
    """
    if Image is None:
        raise RuntimeError(
            "get_image_metadata requires the 'Pillow' package – install it via 'pip install pillow'."
        )

    path = Path(path).expanduser().resolve()

    with Image.open(path) as img, open(path, "rb") as fh:  # type: ignore[arg-type]
        raw_bytes = fh.read()
        sha256 = hashlib.sha256(raw_bytes).hexdigest()

        info: Dict[str, Any] = {
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "bytes": len(raw_bytes),
            "sha256": sha256,
            "exif": _safe_exif(img),
        }

    return info


def fetch_image_with_metadata(
    url: str,
    tmp_dir: Optional[str | os.PathLike[str]] = None,
) -> Dict[str, Any]:
    """Convenience wrapper around :func:`download_image` & :func:`get_image_metadata`.

    It downloads the image, computes metadata and returns a dictionary with
    the structure::

        {
            "file": <pathlib.Path>,
            "mime": "image/jpeg",
            "meta": {...}
        }
    """
    path, mime = download_image(url, tmp_dir=tmp_dir)
    meta = get_image_metadata(path)
    return {"file": path, "mime": mime, "meta": meta} 