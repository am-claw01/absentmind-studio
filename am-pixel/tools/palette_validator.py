"""
palette_validator.py — AM Pixel Project
========================================
Validates sprite palettes for aesthetic quality.

Design philosophy
-----------------
The core pipeline trains on **SNES aesthetic** (art style, palette feel,
outline technique).  Hardware compliance is an *optional* filter applied at
export time (see ``tools/snes_compliance_filter.py``).

Default mode
~~~~~~~~~~~~
Scores aesthetic quality:
  - 0–30 unique colors  → score 1.0  (typical SNES-style sprite)
  - 31–60 unique colors → score 0.7  (a bit rich, but usable)
  - 60+ unique colors   → score 0.3  (may lack SNES aesthetic coherence)

``--snes-strict`` mode
~~~~~~~~~~~~~~~~~~~~~~
Additionally enforces hardware constraints:
  - Every channel must be 0–248 and divisible by 8 (5-bit precision).
  - At most 15 non-transparent colors (slot 0 is implicit transparency).

Usage
-----
  python palette_validator.py sprite.png
  python palette_validator.py sprite.png --snes-strict
  python palette_validator.py sprite.json [--snes-strict]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_hex(hex_color: str) -> tuple[int, int, int]:
    """Return (r, g, b) ints from ``'#RRGGBB'`` or ``'RRGGBB'``."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Expected 6-digit hex color, got: {hex_color!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _aesthetic_score(color_count: int) -> float:
    """Return 0–1 score based on palette size reasonableness."""
    if color_count <= 30:
        return 1.0
    if color_count <= 60:
        return 0.7
    return 0.3


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def count_unique_colors(png_path: str) -> int:
    """Count unique non-transparent RGB colors in a PNG.

    Parameters
    ----------
    png_path : str
        Path to the PNG file.

    Returns
    -------
    int
        Number of unique opaque (alpha ≥ 128) RGB colors.
    """
    from PIL import Image

    img = Image.open(png_path).convert("RGBA")
    seen: set[tuple[int, int, int]] = set()
    for r, g, b, a in img.getdata():
        if a >= 128:
            seen.add((r, g, b))
    return len(seen)


def is_snes_legal_color(r: int, g: int, b: int) -> bool:
    """Return True if every RGB channel is in 0–248 and divisible by 8.

    Intended for use only under ``--snes-strict`` / ``snes_strict=True``.

    Parameters
    ----------
    r, g, b : int
        8-bit channel values.
    """
    for ch in (r, g, b):
        if ch > 248 or ch % 8 != 0:
            return False
    return True


def snes_quantize(r: int, g: int, b: int) -> tuple[int, int, int]:
    """Snap an RGB color to the nearest SNES-compatible value.

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
        return max(0, min(248, round(v / 8) * 8))

    return (_snap(r), _snap(g), _snap(b))


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------

def validate_sprite_png(png_path: str, snes_strict: bool = False) -> dict:
    """Validate a PNG sprite, scoring aesthetic quality by default.

    Parameters
    ----------
    png_path : str
        Path to the PNG file.
    snes_strict : bool
        When True, also enforce 15-bit RGB channels and max 15 colors.

    Returns
    -------
    dict
        ``{color_count, colors, issues, score}``

        - ``color_count`` (int): unique non-transparent colors found.
        - ``colors`` (list[str]): hex strings for each unique color.
        - ``issues`` (list[str]): human-readable problem descriptions.
        - ``score`` (float 0–1): 1.0 = aesthetically great, lower = noisier.

        When ``snes_strict=True`` the dict also contains:

        - ``snes_illegal`` (list[dict]): colors that violate 15-bit rules.
        - ``snes_over_limit`` (int): number of colors above the 15-color cap.
    """
    try:
        from PIL import Image
    except ImportError:
        return {
            "color_count": 0,
            "colors": [],
            "issues": ["Pillow is not installed; cannot validate PNG."],
            "score": 0.0,
        }

    img = Image.open(png_path).convert("RGBA")
    unique_colors: set[tuple[int, int, int]] = set()

    for r, g, b, a in img.getdata():
        if a >= 128:
            unique_colors.add((r, g, b))

    color_count = len(unique_colors)
    colors_hex = [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in sorted(unique_colors)]
    issues: list[str] = []

    score = _aesthetic_score(color_count)

    result: dict = {
        "color_count": color_count,
        "colors": colors_hex,
        "issues": issues,
        "score": score,
    }

    if snes_strict:
        snes_illegal: list[dict] = []
        for r, g, b in unique_colors:
            reasons: list[str] = []
            for name, val in (("R", r), ("G", g), ("B", b)):
                if val > 248:
                    reasons.append(f"{name}={val} > 248")
                elif val % 8 != 0:
                    reasons.append(f"{name}={val} not divisible by 8")
            if reasons:
                snes_illegal.append({
                    "hex": f"#{r:02X}{g:02X}{b:02X}",
                    "reason": "; ".join(reasons),
                })

        snes_over_limit = max(0, color_count - 15)

        if snes_over_limit:
            issues.append(
                f"SNES strict: {color_count} colors found; max 15 allowed. "
                f"{snes_over_limit} color(s) over limit."
            )
        for entry in snes_illegal:
            issues.append(
                f"SNES strict: illegal color {entry['hex']}: {entry['reason']}"
            )

        result["snes_illegal"] = snes_illegal
        result["snes_over_limit"] = snes_over_limit
        # Downgrade score when strict violations exist
        if snes_illegal or snes_over_limit:
            result["score"] = min(score, 0.3)

    return result


def validate_sprite_json(path: str, snes_strict: bool = False) -> dict:
    """Validate a sprite from an indexer JSON sidecar.

    Parameters
    ----------
    path : str
        Path to the sprite JSON file produced by ``indexer.py``.
    snes_strict : bool
        When True, also enforce 15-bit RGB channels and max 15 colors.

    Returns
    -------
    dict
        Same schema as :func:`validate_sprite_png`.
    """
    with open(path, "r", encoding="utf-8") as fh:
        sprite_data = json.load(fh)

    palette: list[str] = sprite_data.get("palette", [])
    color_count = len(palette)
    issues: list[str] = []

    # Parse palette entries
    parsed: list[tuple[int, int, int]] = []
    for hex_color in palette:
        try:
            parsed.append(_parse_hex(hex_color))
        except ValueError:
            issues.append(f"Unparseable hex color in palette: {hex_color!r}")

    score = _aesthetic_score(color_count)

    result: dict = {
        "color_count": color_count,
        "colors": palette,
        "issues": issues,
        "score": score,
    }

    if snes_strict:
        snes_illegal: list[dict] = []
        for r, g, b in parsed:
            reasons: list[str] = []
            for name, val in (("R", r), ("G", g), ("B", b)):
                if val > 248:
                    reasons.append(f"{name}={val} > 248")
                elif val % 8 != 0:
                    reasons.append(f"{name}={val} not divisible by 8")
            if reasons:
                snes_illegal.append({
                    "hex": f"#{r:02X}{g:02X}{b:02X}",
                    "reason": "; ".join(reasons),
                })

        snes_over_limit = max(0, color_count - 15)

        if snes_over_limit:
            issues.append(
                f"SNES strict: {color_count} palette entries; max 15 allowed. "
                f"{snes_over_limit} color(s) over limit."
            )
        for entry in snes_illegal:
            issues.append(
                f"SNES strict: illegal color {entry['hex']}: {entry['reason']}"
            )

        result["snes_illegal"] = snes_illegal
        result["snes_over_limit"] = snes_over_limit
        if snes_illegal or snes_over_limit:
            result["score"] = min(score, 0.3)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """Command-line interface for palette_validator."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate sprite palette aesthetic quality. "
            "By default checks color count reasonableness only. "
            "Use --snes-strict to additionally enforce hardware constraints."
        )
    )
    parser.add_argument("input", help="Path to sprite JSON or PNG file.")
    parser.add_argument(
        "--snes-strict",
        action="store_true",
        default=False,
        help=(
            "Enforce SNES hardware rules: channels 0–248 divisible by 8, "
            "max 15 non-transparent colors."
        ),
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    suffix = input_path.suffix.lower()
    if suffix == ".json":
        result = validate_sprite_json(args.input, snes_strict=args.snes_strict)
        mode = "JSON palette"
    elif suffix == ".png":
        result = validate_sprite_png(args.input, snes_strict=args.snes_strict)
        mode = "PNG colors"
    else:
        print(
            f"ERROR: Unsupported file type '{suffix}'. Pass a .json or .png.",
            file=sys.stderr,
        )
        sys.exit(1)

    mode_tag = " [SNES-strict]" if args.snes_strict else " [aesthetic]"
    print(f"\n=== Palette Validation ({mode}{mode_tag}) ===")
    print(f"  File        : {args.input}")
    print(f"  Color count : {result['color_count']}")
    print(f"  Score       : {result['score']:.2f}")

    if args.snes_strict:
        illegal = result.get("snes_illegal", [])
        over = result.get("snes_over_limit", 0)
        snes_pass = not illegal and not over
        print(f"  SNES-valid  : {'✓ YES' if snes_pass else '✗ NO'}")
        if illegal:
            print(f"\n  SNES illegal colors ({len(illegal)}):")
            for entry in illegal:
                print(f"    {entry['hex']} — {entry['reason']}")

    if result["issues"]:
        print("\n  Issues:")
        for issue in result["issues"]:
            print(f"    • {issue}")
    else:
        print("\n  No issues found.")

    # Exit 1 only when snes_strict is on and there are violations
    if args.snes_strict and result["issues"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
