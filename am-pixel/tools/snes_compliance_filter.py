"""
snes_compliance_filter.py — AM Pixel Project
=============================================
Standalone post-processing filter that enforces SNES hardware compliance.

Design philosophy
-----------------
Hardware compliance is an *export-time* concern, not a training-data concern.
This filter is invoked when the user enables the hardware constraint toggle
(SPEC §10.2).  It must never be called during training data ingestion.

SNES hardware rules applied
-----------------------------
1. Each RGB channel quantized to nearest multiple of 8, clamped to [0, 248]
   (5-bit precision: 0–31 × 8).
2. At most 15 non-transparent colors (slot 0 = implicit transparency).
   Colors beyond the cap are merged into the nearest remaining palette entry.

Usage
-----
  # Single file
  python snes_compliance_filter.py sprite.png out/sprite_snes.png

  # Batch (directory)
  python snes_compliance_filter.py --batch input_dir/ output_dir/
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _snap_channel(v: int) -> int:
    """Round *v* to nearest multiple of 8, clamp to [0, 248]."""
    return max(0, min(248, round(v / 8) * 8))


def _dist_sq(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """Squared Euclidean RGB distance."""
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def _nearest_in_palette(
    color: tuple[int, int, int],
    palette: list[tuple[int, int, int]],
) -> tuple[int, int, int]:
    """Return the palette entry closest to *color*."""
    return min(palette, key=lambda p: _dist_sq(color, p))


def _reduce_palette(
    palette: list[tuple[int, int, int]],
    target: int = 15,
) -> list[tuple[int, int, int]]:
    """Iteratively merge the two closest colors until len ≤ target."""
    pal = list(palette)
    while len(pal) > target:
        best_dist = math.inf
        best_i, best_j = 0, 1
        for i in range(len(pal)):
            for j in range(i + 1, len(pal)):
                d = _dist_sq(pal[i], pal[j])
                if d < best_dist:
                    best_dist = d
                    best_i, best_j = i, j
        ci, cj = pal[best_i], pal[best_j]
        merged = (
            (ci[0] + cj[0]) // 2,
            (ci[1] + cj[1]) // 2,
            (ci[2] + cj[2]) // 2,
        )
        # Re-snap the merged color to 15-bit grid
        merged = (_snap_channel(merged[0]), _snap_channel(merged[1]), _snap_channel(merged[2]))
        pal[best_i] = merged
        pal.pop(best_j)
    # Final deduplication after merges
    seen: set[tuple[int, int, int]] = set()
    deduped: list[tuple[int, int, int]] = []
    for c in pal:
        if c not in seen:
            seen.add(c)
            deduped.append(c)
    return deduped


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_snes_filter(png_path: str, output_path: str) -> dict:
    """Apply SNES hardware compliance to a single PNG.

    Steps
    -----
    1. Quantize every non-transparent pixel to the nearest 15-bit RGB value.
    2. Deduplicate the resulting palette.
    3. If more than 15 unique colors remain, reduce via nearest-pair merging.
    4. Remap every pixel to the final palette; write output PNG.

    Parameters
    ----------
    png_path : str
        Path to the source PNG.
    output_path : str
        Path where the SNES-compliant PNG will be written.

    Returns
    -------
    dict
        ``{original_color_count, final_color_count, colors_merged, output_path}``

        - ``original_color_count`` (int): unique opaque colors before filter.
        - ``final_color_count`` (int): unique opaque colors after filter.
        - ``colors_merged`` (int): how many colors were collapsed.
        - ``output_path`` (str): the path that was written.
    """
    from PIL import Image

    img = Image.open(png_path).convert("RGBA")
    pixels = list(img.getdata())
    w, h = img.size

    # 1. Count original colors & build 15-bit quantized palette
    original_colors: set[tuple[int, int, int]] = set()
    for r, g, b, a in pixels:
        if a >= 128:
            original_colors.add((r, g, b))
    original_color_count = len(original_colors)

    # 2. Snap each to nearest 15-bit value
    quantized_unique: set[tuple[int, int, int]] = set()
    for r, g, b in original_colors:
        quantized_unique.add((_snap_channel(r), _snap_channel(g), _snap_channel(b)))

    palette = sorted(quantized_unique)

    # 3. Reduce if >15 colors
    if len(palette) > 15:
        palette = _reduce_palette(palette, target=15)

    final_color_count = len(palette)
    colors_merged = original_color_count - final_color_count

    # 4. Remap pixels
    out_pixels: list[tuple[int, int, int, int]] = []
    for r, g, b, a in pixels:
        if a < 128:
            out_pixels.append((0, 0, 0, 0))  # transparent
        else:
            qr, qg, qb = _snap_channel(r), _snap_channel(g), _snap_channel(b)
            nr, ng, nb = _nearest_in_palette((qr, qg, qb), palette)
            out_pixels.append((nr, ng, nb, 255))

    # 5. Write output
    out_img = Image.new("RGBA", (w, h))
    out_img.putdata(out_pixels)  # type: ignore[arg-type]
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out_img.save(str(out), "PNG")

    return {
        "original_color_count": original_color_count,
        "final_color_count": final_color_count,
        "colors_merged": colors_merged,
        "output_path": str(out),
    }


def batch_filter(input_dir: str, output_dir: str) -> list[dict]:
    """Apply SNES filter to every PNG in *input_dir*, writing to *output_dir*.

    Parameters
    ----------
    input_dir : str
        Directory containing source PNGs (searched recursively).
    output_dir : str
        Directory where compliant PNGs will be written, mirroring the
        subdirectory structure of *input_dir*.

    Returns
    -------
    list[dict]
        One result dict per PNG processed (same schema as
        :func:`apply_snes_filter`).
    """
    in_path = Path(input_dir)
    out_path = Path(output_dir)
    results: list[dict] = []

    png_files = sorted(in_path.rglob("*.png"))
    if not png_files:
        print(f"[snes_filter] No PNG files found in {input_dir}", file=sys.stderr)
        return results

    for src in png_files:
        rel = src.relative_to(in_path)
        dest = out_path / rel
        try:
            result = apply_snes_filter(str(src), str(dest))
            results.append(result)
            print(
                f"[snes_filter] {src.name}: "
                f"{result['original_color_count']} → {result['final_color_count']} colors "
                f"({result['colors_merged']} merged) → {dest}"
            )
        except Exception as exc:
            print(f"[snes_filter] ERROR processing {src}: {exc}", file=sys.stderr)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """Command-line interface for snes_compliance_filter."""
    parser = argparse.ArgumentParser(
        description=(
            "Apply SNES hardware compliance filter to PNG sprites. "
            "Quantizes to 15-bit RGB and reduces to max 15 non-transparent colors. "
            "Intended for export time only (SPEC §10.2)."
        )
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--batch",
        nargs=2,
        metavar=("INPUT_DIR", "OUTPUT_DIR"),
        help="Process all PNGs in INPUT_DIR and write results to OUTPUT_DIR.",
    )
    mode_group.add_argument(
        "input",
        nargs="?",
        help="Path to a single source PNG.",
    )

    parser.add_argument(
        "output",
        nargs="?",
        help="Path for the output PNG (required when processing a single file).",
    )

    args = parser.parse_args()

    if args.batch:
        input_dir, output_dir = args.batch
        results = batch_filter(input_dir, output_dir)
        total_merged = sum(r["colors_merged"] for r in results)
        print(
            f"\n[snes_filter] Done: {len(results)} file(s) processed, "
            f"{total_merged} total colors merged."
        )
    else:
        if not args.input or not args.output:
            parser.error("Provide both INPUT and OUTPUT paths for single-file mode.")

        src = Path(args.input)
        if not src.exists():
            print(f"ERROR: File not found: {args.input}", file=sys.stderr)
            sys.exit(1)

        result = apply_snes_filter(args.input, args.output)
        print(
            f"\n[snes_filter] {src.name}:\n"
            f"  Original colors : {result['original_color_count']}\n"
            f"  Final colors    : {result['final_color_count']}\n"
            f"  Colors merged   : {result['colors_merged']}\n"
            f"  Output          : {result['output_path']}"
        )


if __name__ == "__main__":
    main()
