"""
indexer.py — AM Pixel Pipeline · Stage 2
Converts sprite PNG images to palette-index format.

The SNES hardware uses 4-bpp (16-colour) palettes where each channel is
stored at 5-bit precision (0–31 → multiply by 8 gives 0–248 in 8-step
increments).  This module:

  1. Extracts the unique non-transparent colours from a sprite.
  2. Optionally reduces the palette to ≤15 colours (slot 0 = transparent).
  3. Validates SNES compatibility.
  4. Builds a flat index grid (0 = transparent, 1-based for real colours).
  5. Writes a JSON file with all of the above for downstream stages.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

from PIL import Image


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _hex(r: int, g: int, b: int) -> str:
    """Return a CSS-style hex string '#rrggbb'."""
    return f"#{r:02x}{g:02x}{b:02x}"


def _dist_sq(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """Squared Euclidean distance between two RGB triples."""
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_palette(image: Image.Image) -> list[tuple[int, int, int]]:
    """
    Return the list of unique non-transparent RGB colours present in *image*.

    Pixels whose alpha < 128 are treated as transparent and excluded.
    The order is deterministic: sorted by (r, g, b) for reproducibility.

    Parameters
    ----------
    image : PIL.Image.Image
        Source image (any mode; converted to RGBA internally).

    Returns
    -------
    list[tuple[int, int, int]]
        Sorted list of unique (r, g, b) colour tuples.
    """
    img = image.convert("RGBA")
    seen: set[tuple[int, int, int]] = set()
    for r, g, b, a in img.getdata():
        if a >= 128:
            seen.add((r, g, b))
    return sorted(seen)


def nearest_color(
    color: tuple[int, int, int],
    palette: list[tuple[int, int, int]],
) -> int:
    """
    Find the palette entry closest to *color* by Euclidean RGB distance.

    Index 0 is reserved for transparent; returned indices are **1-based**.

    Parameters
    ----------
    color : tuple[int, int, int]
        The (r, g, b) colour to look up.
    palette : list[tuple[int, int, int]]
        The palette to search (must be non-empty).

    Returns
    -------
    int
        1-based index of the nearest palette entry, or 0 if *palette* is
        empty (treated as transparent).
    """
    if not palette:
        return 0
    best_idx = 0
    best_dist = math.inf
    for i, entry in enumerate(palette):
        d = _dist_sq(color, entry)
        if d < best_dist:
            best_dist = d
            best_idx = i
    return best_idx + 1  # 1-based; 0 is reserved for transparent


def quantize_to_palette(
    image: Image.Image,
    palette: list[tuple[int, int, int]],
) -> tuple[list[list[int]], list[tuple[int, int, int]]]:
    """
    Map every pixel in *image* to an index in *palette*.

    Parameters
    ----------
    image : PIL.Image.Image
        Source image (converted to RGBA internally).
    palette : list[tuple[int, int, int]]
        The palette to quantize against.

    Returns
    -------
    index_grid : list[list[int]]
        2-D list [row][col] of palette indices.
        0 = transparent; 1-based = colour in *palette*.
    actual_palette : list[tuple[int, int, int]]
        The palette that was used (same object as the input *palette*,
        returned for convenience).
    """
    img = image.convert("RGBA")
    w, h = img.size
    pixels = list(img.getdata())
    grid: list[list[int]] = []
    for row in range(h):
        row_data: list[int] = []
        for col in range(w):
            r, g, b, a = pixels[row * w + col]
            if a < 128:
                row_data.append(0)
            else:
                row_data.append(nearest_color((r, g, b), palette))
        grid.append(row_data)
    return grid, palette


def validate_snes_palette(
    palette: list[tuple[int, int, int]],
) -> bool:
    """
    Return True if *palette* is SNES-compatible.

    Rules
    -----
    * At most 15 colours (slot 0 is implicitly transparent).
    * Every channel value must be in the range 0–248 in steps of 8
      (i.e. a multiple of 8, ≤248).

    Parameters
    ----------
    palette : list[tuple[int, int, int]]

    Returns
    -------
    bool
    """
    if len(palette) > 15:
        return False
    for r, g, b in palette:
        for ch in (r, g, b):
            if ch % 8 != 0 or ch > 248:
                return False
    return True


def snes_quantize_color(r: int, g: int, b: int) -> tuple[int, int, int]:
    """
    Snap an RGB colour to the nearest SNES-compatible value.

    Each channel is rounded to the nearest multiple of 8 and clamped to
    [0, 248].

    Parameters
    ----------
    r, g, b : int
        Input channel values (0–255).

    Returns
    -------
    tuple[int, int, int]
        Quantized (r, g, b).
    """
    def _snap(v: int) -> int:
        snapped = round(v / 8) * 8
        return max(0, min(248, snapped))
    return (_snap(r), _snap(g), _snap(b))


def reduce_palette(
    palette: list[tuple[int, int, int]],
    target: int = 15,
) -> list[tuple[int, int, int]]:
    """
    Reduce *palette* to at most *target* colours by iteratively merging the
    two nearest (closest Euclidean distance) colours into their midpoint.

    Parameters
    ----------
    palette : list[tuple[int, int, int]]
        Input palette (may have more than *target* entries).
    target : int
        Maximum number of output colours.  Default: 15 (SNES limit).

    Returns
    -------
    list[tuple[int, int, int]]
        Reduced palette (≤ *target* entries).
    """
    # Work on a mutable copy; preserve insertion order via list
    pal = list(palette)
    while len(pal) > target:
        # Find the pair with minimum squared distance
        best_dist = math.inf
        best_i = 0
        best_j = 1
        for i in range(len(pal)):
            for j in range(i + 1, len(pal)):
                d = _dist_sq(pal[i], pal[j])
                if d < best_dist:
                    best_dist = d
                    best_i, best_j = i, j
        # Merge: replace pal[best_i] with midpoint, remove pal[best_j]
        ci, cj = pal[best_i], pal[best_j]
        merged = (
            (ci[0] + cj[0]) // 2,
            (ci[1] + cj[1]) // 2,
            (ci[2] + cj[2]) // 2,
        )
        pal[best_i] = merged
        pal.pop(best_j)
    return pal


def index_sprite(image_path: str, output_path: str) -> dict[str, Any]:
    """
    Full indexing pipeline for a single sprite image.

    Steps
    -----
    1. Load the image and convert to RGBA.
    2. Extract unique non-transparent colours.
    3. SNES-quantize every colour (snap to nearest 8-step value).
    4. Deduplicate after quantization.
    5. If >15 colours, reduce palette via colour merging.
    6. Validate SNES compatibility.
    7. Build the index grid (0 = transparent, 1-based otherwise).
    8. Write a JSON file with all metadata.

    Parameters
    ----------
    image_path : str
        Path to the source sprite PNG.
    output_path : str
        Path where the JSON index file will be written.

    Returns
    -------
    dict
        The same data structure that is written to *output_path*:
        ``{sprite_id, width, height, palette, index_grid, transparent_index,
        snes_valid}``.
    """
    img_path = Path(image_path)
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size

    # 1. Extract unique colours
    raw_palette = extract_palette(img)

    # 2. SNES-quantize each colour
    quantized: list[tuple[int, int, int]] = []
    seen_q: set[tuple[int, int, int]] = set()
    for rgb in raw_palette:
        q = snes_quantize_color(*rgb)
        if q not in seen_q:
            seen_q.add(q)
            quantized.append(q)

    # 3. Reduce if necessary
    if len(quantized) > 15:
        quantized = reduce_palette(quantized, target=15)
        # Re-snap after merging
        quantized = [snes_quantize_color(*c) for c in quantized]
        # Deduplicate again
        deduped: list[tuple[int, int, int]] = []
        seen2: set[tuple[int, int, int]] = set()
        for c in quantized:
            if c not in seen2:
                seen2.add(c)
                deduped.append(c)
        quantized = deduped

    snes_ok = validate_snes_palette(quantized)

    # 4. Build index grid using SNES-quantized colour for each pixel
    index_grid, _ = quantize_to_palette(img, quantized)

    # 5. Flatten the grid
    flat_grid = [idx for row in index_grid for idx in row]

    # 6. Build result dict
    sprite_id = img_path.stem
    result: dict[str, Any] = {
        "sprite_id":        sprite_id,
        "width":            w,
        "height":           h,
        "palette":          [_hex(*c) for c in quantized],
        "index_grid":       flat_grid,
        "transparent_index": 0,
        "snes_valid":       snes_ok,
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    print(
        f"[indexer] {sprite_id}: {w}×{h}, "
        f"{len(quantized)} colour(s), "
        f"SNES-valid={snes_ok} → {out}"
    )
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """Command-line interface for the sprite indexer."""
    parser = argparse.ArgumentParser(
        prog="indexer",
        description="Convert a sprite PNG to a palette-index JSON.",
    )
    parser.add_argument(
        "image_path",
        help="Path to the source sprite PNG.",
    )
    parser.add_argument(
        "output_path",
        help="Path for the output JSON index file.",
    )
    args = parser.parse_args()

    try:
        index_sprite(args.image_path, args.output_path)
    except Exception as exc:
        print(f"[indexer] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
