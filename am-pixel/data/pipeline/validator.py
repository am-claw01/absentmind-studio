"""
validator.py — AM Pixel Pipeline: SNES Sprite Validator
========================================================
Validates sprite index-JSON files for SNES palette compliance
and training provenance.

SNES color constraints:
  - 5 bits per channel  →  valid values: 0, 8, 16, …, 248  (step 8)
  - Max 15 non-transparent colors per sprite (index 0 = transparent)

Usage:
    python validator.py <sprite_json>
    python validator.py <sprite_json> --manifest TRAINING_PROVENANCE_MANIFEST.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# SNES color math
# ---------------------------------------------------------------------------

# All valid 8-bit representations of a 5-bit SNES channel: 0,8,16,...,248
_SNES_VALID_CHANNELS: frozenset[int] = frozenset(range(0, 249, 8))


def snes_quantize_color(r: int, g: int, b: int) -> tuple[int, int, int]:
    """
    Snap each RGB channel to the nearest multiple of 8, clamped to [0, 248].
    This maps an arbitrary 24-bit color to its nearest SNES-legal equivalent.
    """
    def _snap(v: int) -> int:
        # Round to nearest multiple of 8
        snapped = round(v / 8) * 8
        return max(0, min(248, snapped))

    return (_snap(r), _snap(g), _snap(b))


def SNES_legal(hex_color: str) -> bool:
    """
    Return True if *hex_color* (e.g. '#FF8800' or 'FF8800') is a legal
    SNES color — each channel must be a multiple of 8 and in [0, 248].
    """
    hex_color = hex_color.lstrip("#").strip()
    if len(hex_color) != 6:
        return False
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except ValueError:
        return False
    return r in _SNES_VALID_CHANNELS and g in _SNES_VALID_CHANNELS and b in _SNES_VALID_CHANNELS


# ---------------------------------------------------------------------------
# Sprite validation
# ---------------------------------------------------------------------------

def validate_sprite(sprite_data: dict) -> dict:
    """
    Validate a sprite index dict (as produced by indexer.py).

    Expected keys: sprite_id, width, height, palette, index_grid,
                   transparent_index (typically 0).

    Returns
    -------
    dict with keys:
      valid  : bool
      issues : list[str]   (empty when valid)
    """
    issues: list[str] = []

    # --- Basic structural checks ---
    for required_key in ("sprite_id", "width", "height", "palette", "index_grid"):
        if required_key not in sprite_data:
            issues.append(f"Missing required key: '{required_key}'")

    if issues:
        # Cannot proceed without structure
        return {"valid": False, "issues": issues}

    width: int = sprite_data["width"]
    height: int = sprite_data["height"]
    palette: list[str] = sprite_data["palette"]
    index_grid: list[int] = sprite_data["index_grid"]

    # --- Dimension checks ---
    if not isinstance(width, int) or width <= 0:
        issues.append(f"Invalid width: {width!r} (must be positive integer)")
    if not isinstance(height, int) or height <= 0:
        issues.append(f"Invalid height: {height!r} (must be positive integer)")

    # --- index_grid size check ---
    expected_pixels = width * height
    actual_pixels = len(index_grid)
    if actual_pixels != expected_pixels:
        issues.append(
            f"index_grid length {actual_pixels} does not match width×height "
            f"({width}×{height}={expected_pixels})"
        )

    # --- Palette count check (SNES: max 15 non-transparent colors) ---
    if len(palette) > 15:
        issues.append(
            f"Palette has {len(palette)} colors; SNES maximum is 15 "
            "(index 0 = transparent, indices 1–15 = colors)"
        )

    # --- SNES color legality ---
    for i, hex_color in enumerate(palette):
        if not SNES_legal(hex_color):
            issues.append(
                f"palette[{i}] = '{hex_color}' is not a valid SNES color "
                "(each channel must be a multiple of 8 in range 0–248)"
            )

    # --- Index range check ---
    max_valid_index = len(palette)   # 0 = transparent, 1..len(palette) valid
    for pixel_idx, val in enumerate(index_grid):
        if not isinstance(val, int) or val < 0 or val > max_valid_index:
            issues.append(
                f"index_grid[{pixel_idx}] = {val!r} out of range "
                f"[0, {max_valid_index}]"
            )
            if len(issues) >= 20:          # cap error flood
                issues.append("… (further index errors suppressed)")
                break

    return {"valid": len(issues) == 0, "issues": issues}


# ---------------------------------------------------------------------------
# Provenance check
# ---------------------------------------------------------------------------

def provenance_check(sprite_id: str, manifest_path: str | Path) -> bool:
    """
    Return True if *sprite_id* is present in the training provenance manifest.

    The manifest is expected to be a JSON file named
    TRAINING_PROVENANCE_MANIFEST.json and may be:
      - A list of dicts with a "sprite_id" key, or
      - A dict keyed by sprite_id, or
      - A list of sprite_id strings.
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        print(
            f"[validator] WARNING: Provenance manifest not found: {manifest_path}",
            file=sys.stderr,
        )
        return False

    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    if isinstance(manifest, dict):
        return sprite_id in manifest

    if isinstance(manifest, list):
        for entry in manifest:
            if isinstance(entry, str) and entry == sprite_id:
                return True
            if isinstance(entry, dict) and entry.get("sprite_id") == sprite_id:
                return True

    return False


# ---------------------------------------------------------------------------
# CLI report helper
# ---------------------------------------------------------------------------

def _print_validation_report(
    sprite_json_path: Path,
    manifest_path: Optional[Path] = None,
) -> bool:
    """Load a sprite JSON, validate, print result. Return overall pass/fail."""
    with open(sprite_json_path, "r", encoding="utf-8") as fh:
        sprite_data = json.load(fh)

    result = validate_sprite(sprite_data)

    sprite_id = sprite_data.get("sprite_id", "<unknown>")
    width = sprite_data.get("width", "?")
    height = sprite_data.get("height", "?")
    n_colors = len(sprite_data.get("palette", []))

    print(f"─── Sprite Validation: {sprite_id} ───")
    print(f"  File   : {sprite_json_path}")
    print(f"  Size   : {width}×{height}")
    print(f"  Colors : {n_colors} / 15")

    if result["valid"]:
        print("  Status : ✓ VALID — all SNES constraints satisfied")
    else:
        print(f"  Status : ✗ INVALID — {len(result['issues'])} issue(s)")
        for issue in result["issues"]:
            print(f"    • {issue}")

    # Provenance
    if manifest_path is not None:
        prov = provenance_check(sprite_id, manifest_path)
        status = "✓ found" if prov else "✗ NOT FOUND"
        print(f"  Provenance: {status}  ({manifest_path.name})")

    return result["valid"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="AM Pixel — SNES Sprite Validator")
    p.add_argument("sprite_json", help="Path to sprite index JSON file")
    p.add_argument(
        "--manifest",
        default=None,
        help="Path to TRAINING_PROVENANCE_MANIFEST.json for provenance check",
    )
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()
    sprite_json_path = Path(args.sprite_json)
    manifest_path = Path(args.manifest) if args.manifest else None

    passed = _print_validation_report(sprite_json_path, manifest_path)
    sys.exit(0 if passed else 1)
