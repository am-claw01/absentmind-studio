"""
pixel_classifier.py — AM Pixel Pipeline · Stage 3
Classifies every pixel in an indexed sprite into structural categories.

CHANGE-014 · 4-category default
--------------------------------
  0 = TRANSPARENT     — alpha == 0 (index == 0)
  1 = OUTLINE         — non-transparent pixel with ≥1 fully-transparent
                        4-neighbour (up/down/left/right)
  2 = STRUCTURAL      — non-transparent, non-outline pixel belonging to a
                        flood-filled region of the same palette-index that
                        has MORE than 6 pixels
  3 = NON_STRUCTURAL  — non-transparent, non-outline pixel belonging to a
                        flood-filled region with ≤6 pixels

Optional --full-five-category
------------------------------
  0 = TRANSPARENT
  1 = OUTLINE
  2 = STRUCTURAL
  3 = SHADE           — small region (≤6 px) that shares ≥1 edge with a
                        STRUCTURAL region
  4 = DETAIL          — everything else (small region not adjacent to
                        structural)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Category constants
# ---------------------------------------------------------------------------

CAT_TRANSPARENT   = 0
CAT_OUTLINE       = 1
CAT_STRUCTURAL    = 2
CAT_NON_STRUCTURAL = 3   # 4-category mode
CAT_SHADE         = 3   # 5-category mode (same slot, different semantics)
CAT_DETAIL        = 4   # 5-category mode only

STRUCTURAL_THRESHOLD = 6  # regions with > this many pixels → STRUCTURAL


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def is_outline(
    x: int,
    y: int,
    grid: list[list[int]],
    w: int,
    h: int,
) -> bool:
    """
    Return True if the pixel at (x, y) is a non-transparent pixel that has
    at least one fully-transparent 4-connected neighbour.

    Parameters
    ----------
    x, y : int
        Pixel coordinates (x = column, y = row).
    grid : list[list[int]]
        2-D index grid (grid[row][col]).  0 = transparent.
    w, h : int
        Image dimensions (width, height).

    Returns
    -------
    bool
    """
    if grid[y][x] == 0:
        return False  # transparent pixel is never an outline

    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nx, ny = x + dx, y + dy
        if nx < 0 or ny < 0 or nx >= w or ny >= h:
            # Treat out-of-bounds as transparent
            return True
        if grid[ny][nx] == 0:
            return True
    return False


def flood_fill_regions(
    grid: list[list[int]],
    w: int,
    h: int,
) -> dict[tuple[int, int], list[tuple[int, int]]]:
    """
    Label every contiguous group of same-index non-transparent pixels as a
    region, using 4-connectivity BFS.

    Parameters
    ----------
    grid : list[list[int]]
        2-D index grid.  0 = transparent.
    w, h : int
        Image dimensions.

    Returns
    -------
    dict mapping (palette_index, region_id) → [(x, y), ...]
        ``palette_index`` is the shared palette index of all pixels in the
        region.  ``region_id`` is an integer counter unique within each
        palette index value.
    """
    visited: list[list[bool]] = [[False] * w for _ in range(h)]
    regions: dict[tuple[int, int], list[tuple[int, int]]] = {}
    region_counter: dict[int, int] = {}  # palette_index → next region_id

    for start_y in range(h):
        for start_x in range(w):
            idx = grid[start_y][start_x]
            if idx == 0 or visited[start_y][start_x]:
                continue

            # BFS
            region_id = region_counter.get(idx, 0)
            region_counter[idx] = region_id + 1
            key = (idx, region_id)
            pixels: list[tuple[int, int]] = []

            queue: deque[tuple[int, int]] = deque()
            queue.append((start_x, start_y))
            visited[start_y][start_x] = True

            while queue:
                cx, cy = queue.popleft()
                pixels.append((cx, cy))
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = cx + dx, cy + dy
                    if (
                        0 <= nx < w
                        and 0 <= ny < h
                        and not visited[ny][nx]
                        and grid[ny][nx] == idx
                    ):
                        visited[ny][nx] = True
                        queue.append((nx, ny))

            regions[key] = pixels

    return regions


def classify_sprite(
    index_grid: list[list[int]],
    width: int,
    height: int,
    five_category: bool = False,
) -> list[list[int]]:
    """
    Classify every pixel in the sprite into structural categories.

    Parameters
    ----------
    index_grid : list[list[int]]
        2-D index grid (index_grid[row][col], 0 = transparent).
    width, height : int
        Image dimensions.
    five_category : bool
        If True, use the 5-category scheme (adds SHADE / DETAIL).
        Default: False (4-category: TRANSPARENT / OUTLINE / STRUCTURAL /
        NON_STRUCTURAL).

    Returns
    -------
    list[list[int]]
        2-D category grid (same shape as *index_grid*).
    """
    grid = index_grid  # alias for brevity
    w, h = width, height

    # Step 1: flood-fill to find all regions
    regions = flood_fill_regions(grid, w, h)

    # Build a map (x, y) → region key for O(1) lookups
    pixel_to_region: dict[tuple[int, int], tuple[int, int]] = {}
    for key, pixels in regions.items():
        for px in pixels:
            pixel_to_region[px] = key

    # Determine which regions are STRUCTURAL (size > STRUCTURAL_THRESHOLD)
    structural_keys: set[tuple[int, int]] = {
        k for k, pxs in regions.items() if len(pxs) > STRUCTURAL_THRESHOLD
    }

    # Step 2: build outline mask
    outline: list[list[bool]] = [
        [is_outline(x, y, grid, w, h) for x in range(w)]
        for y in range(h)
    ]

    # Step 3: for 5-category mode, find which small regions are adjacent to
    # a structural region (→ SHADE)
    shade_keys: set[tuple[int, int]] = set()
    if five_category:
        # Collect all pixels belonging to structural regions into a set
        structural_pixels: set[tuple[int, int]] = set()
        for k in structural_keys:
            for px in regions[k]:
                structural_pixels.add(px)

        for key, pxs in regions.items():
            if key in structural_keys:
                continue
            # Check if any pixel in this small region neighbours a structural px
            for px, py in pxs:
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = px + dx, py + dy
                    if (nx, ny) in structural_pixels:
                        shade_keys.add(key)
                        break
                if key in shade_keys:
                    break

    # Step 4: assemble category grid
    cat_grid: list[list[int]] = []
    for y in range(h):
        row: list[int] = []
        for x in range(w):
            idx = grid[y][x]
            if idx == 0:
                row.append(CAT_TRANSPARENT)
            elif outline[y][x]:
                row.append(CAT_OUTLINE)
            else:
                rk = pixel_to_region.get((x, y))
                if rk in structural_keys:
                    row.append(CAT_STRUCTURAL)
                elif five_category:
                    if rk in shade_keys:
                        row.append(CAT_SHADE)     # == 3
                    else:
                        row.append(CAT_DETAIL)    # == 4
                else:
                    row.append(CAT_NON_STRUCTURAL)  # == 3
        cat_grid.append(row)

    return cat_grid


def get_distribution(
    category_grid: list[list[int]],
) -> dict[str, Any]:
    """
    Compute the pixel count and percentage for each category present in
    *category_grid*.

    Parameters
    ----------
    category_grid : list[list[int]]
        2-D category grid produced by :func:`classify_sprite`.

    Returns
    -------
    dict
        ``{ category_id (int): {"count": int, "pct": float}, ... }``
        where *pct* is rounded to 2 decimal places.
    """
    counts: dict[int, int] = {}
    total = 0
    for row in category_grid:
        for cat in row:
            counts[cat] = counts.get(cat, 0) + 1
            total += 1

    distribution: dict[str, Any] = {}
    for cat in sorted(counts):
        cnt = counts[cat]
        distribution[cat] = {
            "count": cnt,
            "pct":   round(cnt / total * 100, 2) if total else 0.0,
        }
    return distribution


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_CATEGORY_NAMES_4 = {
    0: "TRANSPARENT",
    1: "OUTLINE",
    2: "STRUCTURAL",
    3: "NON_STRUCTURAL",
}
_CATEGORY_NAMES_5 = {
    0: "TRANSPARENT",
    1: "OUTLINE",
    2: "STRUCTURAL",
    3: "SHADE",
    4: "DETAIL",
}


def main() -> None:
    """Command-line interface for the pixel classifier."""
    parser = argparse.ArgumentParser(
        prog="pixel_classifier",
        description="Classify sprite pixels into structural categories.",
    )
    parser.add_argument(
        "sprite_json",
        help="Path to an indexed sprite JSON file (produced by indexer.py).",
    )
    parser.add_argument(
        "output_json",
        help="Path for the output category-grid JSON file.",
    )
    parser.add_argument(
        "--full-five-category",
        action="store_true",
        default=False,
        help="Use the 5-category scheme (adds SHADE and DETAIL).",
    )

    args = parser.parse_args()

    try:
        # Load indexed sprite
        with open(args.sprite_json, encoding="utf-8") as fh:
            sprite = json.load(fh)

        w: int = sprite["width"]
        h: int = sprite["height"]
        flat: list[int] = sprite["index_grid"]

        # Reconstruct 2-D grid
        index_grid: list[list[int]] = [
            flat[row * w : row * w + w] for row in range(h)
        ]

        five = args.full_five_category
        cat_grid = classify_sprite(index_grid, w, h, five_category=five)
        dist = get_distribution(cat_grid)

        # Flatten category grid for JSON storage
        flat_cat = [cat for row in cat_grid for cat in row]
        names = _CATEGORY_NAMES_5 if five else _CATEGORY_NAMES_4
        output = {
            "sprite_id":      sprite.get("sprite_id", Path(args.sprite_json).stem),
            "width":          w,
            "height":         h,
            "five_category":  five,
            "category_grid":  flat_cat,
            "distribution":   dist,
        }

        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(output, fh, indent=2)

        # Print distribution
        mode_label = "5-category" if five else "4-category"
        print(f"[classifier] {output['sprite_id']} · {mode_label} · {w}×{h}")
        print(f"{'Category':<20} {'Count':>8} {'%':>8}")
        print("-" * 40)
        for cat_id, stats in dist.items():
            label = names.get(int(cat_id), f"CAT_{cat_id}")
            print(f"{label:<20} {stats['count']:>8} {stats['pct']:>7.2f}%")
        print(f"\n[classifier] Written → {out_path}")

    except Exception as exc:
        print(f"[classifier] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
