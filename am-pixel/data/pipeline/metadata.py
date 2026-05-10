"""
data/pipeline/metadata.py
=========================
Sprite provenance metadata utilities for AM Pixel.

Provides:
  - compute_phash()           — 64-bit average perceptual hash (16-char hex)
  - build_provenance_entry()  — construct a full provenance record dict
  - write_provenance_entry()  — atomically append an entry to a JSON manifest
  - read_manifest()           — load all entries from a manifest file
  - main()                    — argparse CLI demo

Requires: Python 3.14+, Pillow. No numpy/cv2.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image


# ---------------------------------------------------------------------------
# Perceptual hash
# ---------------------------------------------------------------------------

def compute_phash(image_path: str | Path) -> str:
    """Compute a 64-bit average perceptual hash for *image_path*.

    Algorithm
    ---------
    1. Open the image and convert to 8-bit grayscale (``'L'`` mode).
    2. Resize to 8 × 8 pixels with ``Image.LANCZOS`` for consistency.
    3. Read all 64 pixel values into a flat list.
    4. Compute the arithmetic mean of those values.
    5. Build a 64-bit integer: bit *i* is 1 if ``pixels[i] >= mean``,
       else 0 (MSB = pixel 0).
    6. Format as a zero-padded 16-character hexadecimal string.

    Parameters
    ----------
    image_path:
        Path to the source image (any format Pillow can read).

    Returns
    -------
    str
        A 16-character lowercase hex string representing the hash.

    Examples
    --------
    >>> h = compute_phash("sprite.png")
    >>> assert len(h) == 16
    """
    img = Image.open(image_path).convert("L").resize((8, 8), Image.LANCZOS)
    pixels = list(img.getdata())          # 64 values, 0-255
    mean = sum(pixels) / len(pixels)

    bits = 0
    for px in pixels:
        bits = (bits << 1) | (1 if px >= mean else 0)

    return f"{bits:016x}"


# ---------------------------------------------------------------------------
# Provenance entry construction
# ---------------------------------------------------------------------------

def build_provenance_entry(
    sprite_id: str,
    source_url: str,
    creator: str,
    license: str,
    license_url: str,
    image_path: str | Path,
    tier: str,
    genre_hint: str = "",
    platform_hint: str = "",
) -> dict[str, Any]:
    """Build a complete provenance metadata record for a sprite.

    Opens *image_path* to extract pixel dimensions and compute the
    perceptual hash. All other fields are supplied by the caller.

    Parameters
    ----------
    sprite_id:
        Unique identifier for the sprite (e.g. ``"hero_walk_01"``).
    source_url:
        URL where the sprite was originally obtained.
    creator:
        Name or handle of the original creator / rights holder.
    license:
        Short license identifier (e.g. ``"CC-BY-4.0"``, ``"OGA-BY-3.0"``).
    license_url:
        Full URL to the license text.
    image_path:
        Filesystem path to the sprite PNG/image.
    tier:
        Quality tier classification (e.g. ``"gold"``, ``"silver"``, ``"bronze"``).
    genre_hint:
        Optional genre tag (e.g. ``"fantasy"``, ``"sci-fi"``).
    platform_hint:
        Optional platform tag (e.g. ``"rpg"``, ``"platformer"``).

    Returns
    -------
    dict
        A dictionary with the following keys:

        ``sprite_id``, ``source_url``, ``creator``, ``license``,
        ``license_url``, ``date_added`` (ISO 8601 UTC), ``perceptual_hash``,
        ``copyright_filter_status``, ``tier``, ``width``, ``height``,
        ``genre_hint``, ``platform_hint``.

    Notes
    -----
    ``copyright_filter_status`` is set to ``"pending"`` by default; downstream
    review tools are expected to update this field after manual or automated
    clearance checks.
    """
    image_path = Path(image_path)
    with Image.open(image_path) as img:
        width, height = img.size

    phash = compute_phash(image_path)
    date_added = datetime.now(timezone.utc).isoformat()

    return {
        "sprite_id": sprite_id,
        "source_url": source_url,
        "creator": creator,
        "license": license,
        "license_url": license_url,
        "date_added": date_added,
        "perceptual_hash": phash,
        "copyright_filter_status": "pending",
        "tier": tier,
        "width": width,
        "height": height,
        "genre_hint": genre_hint,
        "platform_hint": platform_hint,
    }


# ---------------------------------------------------------------------------
# Atomic manifest I/O
# ---------------------------------------------------------------------------

def write_provenance_entry(manifest_path: str | Path, entry: dict[str, Any]) -> None:
    """Atomically append *entry* to the JSON manifest at *manifest_path*.

    The manifest is a JSON file whose top-level value is an array of
    provenance dicts.  This function uses ``fcntl.flock`` to obtain an
    exclusive advisory lock before reading, appending, and rewriting the
    file, so concurrent writers from multiple processes do not corrupt data.

    Parameters
    ----------
    manifest_path:
        Path to the target ``manifest.json`` file.  Created (with an empty
        array) if it does not yet exist.
    entry:
        A provenance dict as returned by :func:`build_provenance_entry`.

    Raises
    ------
    json.JSONDecodeError
        If the existing manifest file contains invalid JSON.
    """
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    # Open (or create) the file in read+write mode without truncating.
    flags = os.O_RDWR | os.O_CREAT
    fd = os.open(manifest_path, flags, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)          # exclusive lock
        with os.fdopen(fd, "r+", closefd=False) as fh:
            raw = fh.read().strip()
            entries: list[dict] = json.loads(raw) if raw else []
            entries.append(entry)
            fh.seek(0)
            fh.write(json.dumps(entries, indent=2, ensure_ascii=False))
            fh.truncate()
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def read_manifest(manifest_path: str | Path) -> list[dict[str, Any]]:
    """Load all provenance entries from *manifest_path*.

    Parameters
    ----------
    manifest_path:
        Path to a ``manifest.json`` file produced by
        :func:`write_provenance_entry`.

    Returns
    -------
    list[dict]
        Parsed list of provenance entry dicts.  Returns an empty list if the
        file does not exist or is empty.

    Raises
    ------
    json.JSONDecodeError
        If the file exists but contains malformed JSON.
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        return []
    raw = manifest_path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    return json.loads(raw)


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

def main() -> None:
    """Command-line interface for metadata operations.

    Sub-commands
    ------------
    add
        Build a provenance entry from CLI flags and append it to a manifest.
    show
        Pretty-print all entries in an existing manifest.
    hash
        Print the perceptual hash of a single image file.

    Examples
    --------
    ::

        python metadata.py hash sprite.png
        python metadata.py add --manifest manifest.json --sprite-id hero_01 \\
            --source-url https://example.com/sprite.png --creator Alice \\
            --license CC-BY-4.0 --license-url https://creativecommons.org/licenses/by/4.0/ \\
            --image sprite.png --tier gold --genre fantasy
        python metadata.py show --manifest manifest.json
    """
    parser = argparse.ArgumentParser(
        prog="metadata",
        description="AM Pixel — sprite provenance metadata utilities",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- hash sub-command ---
    p_hash = sub.add_parser("hash", help="Print the perceptual hash of an image")
    p_hash.add_argument("image", help="Path to image file")

    # --- add sub-command ---
    p_add = sub.add_parser("add", help="Append a provenance entry to a manifest")
    p_add.add_argument("--manifest", required=True, help="Path to manifest.json")
    p_add.add_argument("--sprite-id", required=True, help="Unique sprite ID")
    p_add.add_argument("--source-url", required=True, help="Original source URL")
    p_add.add_argument("--creator", required=True, help="Creator name/handle")
    p_add.add_argument("--license", required=True, help="License identifier (e.g. CC-BY-4.0)")
    p_add.add_argument("--license-url", required=True, help="URL to license text")
    p_add.add_argument("--image", required=True, help="Path to the sprite image")
    p_add.add_argument("--tier", required=True, choices=["gold", "silver", "bronze", "unrated"],
                       help="Quality tier")
    p_add.add_argument("--genre", default="", dest="genre_hint", help="Optional genre tag")
    p_add.add_argument("--platform", default="", dest="platform_hint",
                       help="Optional platform tag")

    # --- show sub-command ---
    p_show = sub.add_parser("show", help="Display all entries in a manifest")
    p_show.add_argument("--manifest", required=True, help="Path to manifest.json")

    args = parser.parse_args()

    if args.command == "hash":
        print(compute_phash(args.image))

    elif args.command == "add":
        entry = build_provenance_entry(
            sprite_id=args.sprite_id,
            source_url=args.source_url,
            creator=args.creator,
            license=args.license,
            license_url=args.license_url,
            image_path=args.image,
            tier=args.tier,
            genre_hint=args.genre_hint,
            platform_hint=args.platform_hint,
        )
        write_provenance_entry(args.manifest, entry)
        print(f"[metadata] Entry '{args.sprite_id}' written to {args.manifest}")
        print(json.dumps(entry, indent=2))

    elif args.command == "show":
        entries = read_manifest(args.manifest)
        if not entries:
            print("[metadata] Manifest is empty or does not exist.")
            sys.exit(0)
        print(f"[metadata] {len(entries)} entries in {args.manifest}:\n")
        print(json.dumps(entries, indent=2))


if __name__ == "__main__":
    main()
