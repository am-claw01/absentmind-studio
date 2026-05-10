"""
extractor.py — AM Pixel Pipeline · Stage 1
Extracts individual sprites from sprite sheets.

Modes
-----
grid : slice the sheet into NxM tiles of fixed size (tile_w × tile_h).
       Tiles that are >95 % transparent are skipped.
       Each kept tile is further cropped to its tight bounding box.
auto : scan rows/columns for fully-transparent gutters; every contiguous
       non-transparent bounding box becomes one sprite.

Output
------
Individual PNGs saved to output_dir, plus a manifest.json that lists
every extracted sprite with its metadata.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from PIL import Image


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_rgba(img: Image.Image) -> Image.Image:
    """Return *img* as an RGBA image, converting from RGB if necessary."""
    if img.mode == "RGBA":
        return img
    if img.mode == "RGB":
        return img.convert("RGBA")
    # Palette, L, LA, etc. — go through RGBA for safety
    return img.convert("RGBA")


def _transparency_ratio(img: Image.Image) -> float:
    """Return the fraction of pixels whose alpha == 0."""
    assert img.mode == "RGBA"
    pixels = list(img.getdata())
    if not pixels:
        return 1.0
    transparent = sum(1 for p in pixels if p[3] == 0)
    return transparent / len(pixels)


def _tight_bbox(img: Image.Image):
    """
    Return the tight bounding box (left, upper, right, lower) of
    non-transparent pixels, or None if the image is fully transparent.
    """
    assert img.mode == "RGBA"
    bbox = img.getbbox()  # Pillow returns None when fully transparent
    return bbox


# ---------------------------------------------------------------------------
# Grid mode
# ---------------------------------------------------------------------------

def _extract_grid(
    sheet: Image.Image,
    output_dir: Path,
    sheet_path: str,
    tile_w: int,
    tile_h: int,
    min_size: int,
) -> list[dict[str, Any]]:
    """
    Slice *sheet* into fixed-size tiles, skip near-fully-transparent ones,
    crop each kept tile to its tight bounding box, and save PNGs.
    """
    sheet_w, sheet_h = sheet.size
    cols = sheet_w // tile_w
    rows = sheet_h // tile_h

    manifest: list[dict[str, Any]] = []
    sprite_id = 0

    for row in range(rows):
        for col in range(cols):
            left   = col * tile_w
            upper  = row * tile_h
            right  = left + tile_w
            lower  = upper + tile_h

            tile = sheet.crop((left, upper, right, lower))

            # Skip tiles that are >95 % transparent
            if _transparency_ratio(tile) > 0.95:
                continue

            # Crop to tight bounding box
            bbox = _tight_bbox(tile)
            if bbox is None:
                continue
            cropped = tile.crop(bbox)
            cw, ch = cropped.size

            # Discard tiny artifacts
            if cw < min_size or ch < min_size:
                continue

            out_name = f"sprite_{sprite_id:04d}.png"
            out_path = output_dir / out_name
            cropped.save(out_path, "PNG")

            manifest.append({
                "sprite_id":    sprite_id,
                "source_sheet": sheet_path,
                "sheet_x":      left + bbox[0],
                "sheet_y":      upper + bbox[1],
                "width":        cw,
                "height":       ch,
                "output_path":  str(out_path),
            })
            sprite_id += 1

    return manifest


# ---------------------------------------------------------------------------
# Auto mode
# ---------------------------------------------------------------------------

def _is_col_transparent(sheet: Image.Image, x: int) -> bool:
    """Return True if every pixel in column *x* is fully transparent."""
    w, h = sheet.size
    for y in range(h):
        if sheet.getpixel((x, y))[3] != 0:
            return False
    return True


def _is_row_transparent(sheet: Image.Image, y: int) -> bool:
    """Return True if every pixel in row *y* is fully transparent."""
    w, h = sheet.size
    for x in range(w):
        if sheet.getpixel((x, y))[3] != 0:
            return False
    return True


def _contiguous_ranges(flags: list[bool]) -> list[tuple[int, int]]:
    """
    Given a list of booleans (True = opaque / non-gutter), return
    [(start, end), ...] slices of contiguous True runs (end is exclusive).
    """
    ranges: list[tuple[int, int]] = []
    in_run = False
    start = 0
    for i, v in enumerate(flags):
        if v and not in_run:
            start = i
            in_run = True
        elif not v and in_run:
            ranges.append((start, i))
            in_run = False
    if in_run:
        ranges.append((start, len(flags)))
    return ranges


def _extract_auto(
    sheet: Image.Image,
    output_dir: Path,
    sheet_path: str,
    min_size: int,
) -> list[dict[str, Any]]:
    """
    Find sprites by scanning for transparent-gutter separations, both
    horizontally (row gutters) and vertically (column gutters).
    """
    w, h = sheet.size

    row_opaque = [not _is_row_transparent(sheet, y) for y in range(h)]
    col_opaque = [not _is_col_transparent(sheet, x) for x in range(w)]

    row_bands = _contiguous_ranges(row_opaque)
    col_bands = _contiguous_ranges(col_opaque)

    manifest: list[dict[str, Any]] = []
    sprite_id = 0

    for r_start, r_end in row_bands:
        for c_start, c_end in col_bands:
            region = sheet.crop((c_start, r_start, c_end, r_end))

            if _transparency_ratio(region) > 0.95:
                continue

            bbox = _tight_bbox(region)
            if bbox is None:
                continue
            cropped = region.crop(bbox)
            cw, ch = cropped.size

            if cw < min_size or ch < min_size:
                continue

            out_name = f"sprite_{sprite_id:04d}.png"
            out_path = output_dir / out_name
            cropped.save(out_path, "PNG")

            manifest.append({
                "sprite_id":    sprite_id,
                "source_sheet": sheet_path,
                "sheet_x":      c_start + bbox[0],
                "sheet_y":      r_start + bbox[1],
                "width":        cw,
                "height":       ch,
                "output_path":  str(out_path),
            })
            sprite_id += 1

    return manifest


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_sheet(
    sheet_path: str,
    output_dir: str,
    mode: str = "grid",
    tile_w: int = 16,
    tile_h: int = 16,
    min_size: int = 8,
) -> list[dict[str, Any]]:
    """
    Extract individual sprites from a sprite sheet.

    Parameters
    ----------
    sheet_path : str
        Path to the source sprite-sheet image (PNG, BMP, …).
    output_dir : str
        Directory where extracted PNGs and manifest.json will be saved.
    mode : {'grid', 'auto'}
        Extraction strategy (see module docstring).
    tile_w : int
        Tile width in pixels (grid mode only).
    tile_h : int
        Tile height in pixels (grid mode only).
    min_size : int
        Minimum pixel dimension (width AND height) a sprite must have to
        be kept.

    Returns
    -------
    list[dict]
        Manifest list.  Each entry has keys:
        sprite_id, source_sheet, sheet_x, sheet_y, width, height, output_path.
        The same data is written to ``<output_dir>/manifest.json``.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(sheet_path)
    sheet = _ensure_rgba(img)

    if mode == "grid":
        manifest = _extract_grid(
            sheet, out_dir, sheet_path, tile_w, tile_h, min_size
        )
    elif mode == "auto":
        manifest = _extract_auto(sheet, out_dir, sheet_path, min_size)
    else:
        raise ValueError(f"Unknown mode {mode!r}. Choose 'grid' or 'auto'.")

    manifest_path = out_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    print(
        f"[extractor] Extracted {len(manifest)} sprite(s) → {out_dir}  "
        f"(manifest: {manifest_path})"
    )
    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """Command-line interface for the sprite extractor."""
    parser = argparse.ArgumentParser(
        prog="extractor",
        description="Extract sprites from a sprite sheet.",
    )
    parser.add_argument(
        "sheet_path",
        help="Path to the source sprite-sheet image.",
    )
    parser.add_argument(
        "output_dir",
        help="Directory to write extracted PNGs and manifest.json.",
    )
    parser.add_argument(
        "--mode",
        choices=["grid", "auto"],
        default="grid",
        help="Extraction mode: 'grid' (fixed tiles) or 'auto' (gutter scan). "
             "Default: grid.",
    )
    parser.add_argument(
        "--tile-w",
        type=int,
        default=16,
        metavar="PX",
        help="Tile width in pixels (grid mode). Default: 16.",
    )
    parser.add_argument(
        "--tile-h",
        type=int,
        default=16,
        metavar="PX",
        help="Tile height in pixels (grid mode). Default: 16.",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=8,
        metavar="PX",
        help="Minimum sprite dimension to keep. Default: 8.",
    )

    args = parser.parse_args()

    try:
        manifest = extract_sheet(
            sheet_path=args.sheet_path,
            output_dir=args.output_dir,
            mode=args.mode,
            tile_w=args.tile_w,
            tile_h=args.tile_h,
            min_size=args.min_size,
        )
        print(f"[extractor] Done. {len(manifest)} sprite(s) extracted.")
    except Exception as exc:
        print(f"[extractor] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
