"""
sequence_reorderer.py — AM Pixel Pipeline · Stage 4
Reorders sprite pixel tokens into a structure-aware sequence suitable for
autoregressive modelling.

Ordering priority
-----------------
  transparent   → rendered last / suppressed (index 0)
  outline       → first meaningful group  (category 1)
  structural    → second group            (category 2)
  non-structural/shade/detail → remainder (categories 3, 4)

Within each group pixels are emitted in raster order (top-to-bottom,
left-to-right).  Transparent pixels are placed at the very end of the
sequence (they carry no colour information but occupy canvas positions).

Token format
------------
Each token is a 3-tuple ``(palette_index, canvas_x, canvas_y)`` where
``palette_index`` is the value from the index grid (0 = transparent,
1-based for real colours).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Category ordering
# ---------------------------------------------------------------------------

# Lower priority → earlier in output sequence.
# All non-structural categories (3 and above) share the same priority.
_PRIORITY: dict[int, int] = {
    0: 3,   # TRANSPARENT      — last
    1: 0,   # OUTLINE          — first
    2: 1,   # STRUCTURAL       — second
    3: 2,   # NON_STRUCTURAL / SHADE
    4: 2,   # DETAIL
}


def _category_priority(cat: int) -> int:
    """Return the ordering priority for a category (lower = earlier)."""
    return _PRIORITY.get(cat, 2)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def reorder_sprite(
    index_grid: list[list[int]],
    category_grid: list[list[int]],
    width: int,
    height: int,
) -> list[tuple[int, int, int]]:
    """
    Reorder sprite pixel tokens into structure-aware sequence order.

    Parameters
    ----------
    index_grid : list[list[int]]
        2-D palette-index grid (index_grid[row][col], 0 = transparent).
    category_grid : list[list[int]]
        2-D category grid produced by ``pixel_classifier.classify_sprite``.
    width, height : int
        Image dimensions.

    Returns
    -------
    list[tuple[int, int, int]]
        Ordered list of ``(palette_index, canvas_x, canvas_y)`` tokens.

        Order:
        1. OUTLINE pixels      (category 1)  — raster order within group
        2. STRUCTURAL pixels   (category 2)  — raster order within group
        3. NON_STRUCTURAL / SHADE / DETAIL pixels (categories ≥3, excluding
           transparent) — raster order within group
        4. TRANSPARENT pixels  (category 0)  — raster order within group
    """
    # Collect pixels per priority bucket (use a dict of lists)
    buckets: dict[int, list[tuple[int, int, int]]] = {0: [], 1: [], 2: [], 3: []}

    for y in range(height):
        for x in range(width):
            cat = category_grid[y][x]
            pal_idx = index_grid[y][x]
            priority = _category_priority(cat)
            buckets[priority].append((pal_idx, x, y))

    # Concatenate in priority order (0 → 1 → 2 → 3)
    sequence: list[tuple[int, int, int]] = []
    for p in range(4):
        sequence.extend(buckets[p])
    return sequence


def save_sequence(
    sequence: list[tuple[int, int, int]],
    output_path: str,
) -> None:
    """
    Persist a pixel sequence to a JSON file.

    Each token is stored as a compact object ``{p, x, y}``.

    Parameters
    ----------
    sequence : list[tuple[int, int, int]]
        The sequence returned by :func:`reorder_sprite`.
    output_path : str
        Destination file path (parent directories created automatically).
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"p": p, "x": x, "y": y} for p, x, y in sequence]
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    print(f"[reorderer] Saved {len(sequence)} token(s) → {out}")


def load_sequence(path: str) -> list[tuple[int, int, int]]:
    """
    Load a pixel sequence from a JSON file previously written by
    :func:`save_sequence`.

    Parameters
    ----------
    path : str
        Path to the sequence JSON file.

    Returns
    -------
    list[tuple[int, int, int]]
        List of ``(palette_index, canvas_x, canvas_y)`` tuples.
    """
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return [(tok["p"], tok["x"], tok["y"]) for tok in raw]


def get_distribution(
    category_grid: list[list[int]],
) -> dict[str, Any]:
    """
    Compute the pixel count and percentage for each category in
    *category_grid*.

    This is a convenience duplicate of the same function in
    ``pixel_classifier`` so that the reorderer can be used standalone.

    Parameters
    ----------
    category_grid : list[list[int]]
        2-D category grid.

    Returns
    -------
    dict
        ``{ category_id (int): {"count": int, "pct": float} }``
    """
    counts: dict[int, int] = {}
    total = 0
    for row in category_grid:
        for cat in row:
            counts[cat] = counts.get(cat, 0) + 1
            total += 1

    result: dict[str, Any] = {}
    for cat in sorted(counts):
        cnt = counts[cat]
        result[cat] = {
            "count": cnt,
            "pct":   round(cnt / total * 100, 2) if total else 0.0,
        }
    return result


def process_sprite_file(
    sprite_json_path: str,
    category_json_path: str,
    output_path: str,
) -> list[tuple[int, int, int]]:
    """
    End-to-end helper: load an indexed sprite JSON and its category JSON,
    reorder the tokens, and write the sequence to *output_path*.

    Parameters
    ----------
    sprite_json_path : str
        Path to the indexed sprite JSON (produced by ``indexer.py``).
    category_json_path : str
        Path to the category JSON (produced by ``pixel_classifier.py``).
    output_path : str
        Destination path for the sequence JSON.

    Returns
    -------
    list[tuple[int, int, int]]
        The reordered sequence of ``(palette_index, canvas_x, canvas_y)``
        tokens.
    """
    # Load sprite
    with open(sprite_json_path, encoding="utf-8") as fh:
        sprite = json.load(fh)
    w: int = sprite["width"]
    h: int = sprite["height"]
    flat_idx: list[int] = sprite["index_grid"]

    # Load category grid
    with open(category_json_path, encoding="utf-8") as fh:
        cat_data = json.load(fh)
    flat_cat: list[int] = cat_data["category_grid"]

    # Validate dimensions
    if len(flat_idx) != w * h:
        raise ValueError(
            f"index_grid length {len(flat_idx)} ≠ {w}×{h}={w*h}"
        )
    if len(flat_cat) != w * h:
        raise ValueError(
            f"category_grid length {len(flat_cat)} ≠ {w}×{h}={w*h}"
        )

    # Reconstruct 2-D grids
    index_grid: list[list[int]] = [
        flat_idx[row * w : row * w + w] for row in range(h)
    ]
    category_grid: list[list[int]] = [
        flat_cat[row * w : row * w + w] for row in range(h)
    ]

    sequence = reorder_sprite(index_grid, category_grid, w, h)
    save_sequence(sequence, output_path)
    return sequence


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """Command-line interface for the sequence reorderer."""
    parser = argparse.ArgumentParser(
        prog="sequence_reorderer",
        description=(
            "Reorder sprite pixel tokens into structure-aware sequence order "
            "(outline → structural → non-structural → transparent)."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ---- process sub-command ----
    proc = subparsers.add_parser(
        "process",
        help="Full end-to-end: load sprite + category JSONs, write sequence.",
    )
    proc.add_argument(
        "sprite_json",
        help="Path to indexed sprite JSON (from indexer.py).",
    )
    proc.add_argument(
        "category_json",
        help="Path to category JSON (from pixel_classifier.py).",
    )
    proc.add_argument(
        "output_path",
        help="Destination path for the sequence JSON.",
    )

    # ---- inspect sub-command ----
    insp = subparsers.add_parser(
        "inspect",
        help="Load an existing sequence JSON and print a summary.",
    )
    insp.add_argument(
        "sequence_json",
        help="Path to a sequence JSON file.",
    )

    # ---- distribution sub-command ----
    dist_cmd = subparsers.add_parser(
        "distribution",
        help="Print the category distribution from a category JSON.",
    )
    dist_cmd.add_argument(
        "category_json",
        help="Path to a category JSON file (from pixel_classifier.py).",
    )

    args = parser.parse_args()

    try:
        if args.command == "process":
            seq = process_sprite_file(
                args.sprite_json,
                args.category_json,
                args.output_path,
            )
            print(f"[reorderer] Sequence length: {len(seq)} token(s).")

        elif args.command == "inspect":
            seq = load_sequence(args.sequence_json)
            print(f"[reorderer] {args.sequence_json}: {len(seq)} token(s).")
            if seq:
                print(f"  First token : p={seq[0][0]}, x={seq[0][1]}, y={seq[0][2]}")
                print(f"  Last  token : p={seq[-1][0]}, x={seq[-1][1]}, y={seq[-1][2]}")

        elif args.command == "distribution":
            with open(args.category_json, encoding="utf-8") as fh:
                cat_data = json.load(fh)
            w: int = cat_data["width"]
            h: int = cat_data["height"]
            flat_cat: list[int] = cat_data["category_grid"]
            cat_grid: list[list[int]] = [
                flat_cat[row * w : row * w + w] for row in range(h)
            ]
            dist = get_distribution(cat_grid)

            five = cat_data.get("five_category", False)
            names = {
                0: "TRANSPARENT",
                1: "OUTLINE",
                2: "STRUCTURAL",
                3: "SHADE" if five else "NON_STRUCTURAL",
                4: "DETAIL",
            }
            print(f"[reorderer] Category distribution · {w}×{h}")
            print(f"{'Category':<20} {'Count':>8} {'%':>8}")
            print("-" * 40)
            for cat_id, stats in dist.items():
                label = names.get(int(cat_id), f"CAT_{cat_id}")
                print(f"{label:<20} {stats['count']:>8} {stats['pct']:>7.2f}%")

    except Exception as exc:
        print(f"[reorderer] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
