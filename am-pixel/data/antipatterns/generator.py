"""
data/antipatterns/generator.py
==============================
Generates intentionally bad pixel-art sprites and their corrected counterparts
for evaluation calibration in the AM Pixel pipeline.

All sprites are 16 × 24 pixels, saved as PNG.

Failure modes (bad + corrected pair each)
-----------------------------------------
1.  pillow_shading      — smooth circular gradient (bad) vs flat regions + hue ramp (correct)
2.  color_banding       — grey brightness bands, no hue shift (bad) vs hue-shifted ramp (correct)
3.  pure_black_outline  — #000000 border (bad) vs darkened local-color border (correct)
4.  random_dithering    — random noise pixels (bad) vs structured checkerboard (correct)
5.  palette_bloat       — 20+ distinct colors (bad) vs ≤15 colors (correct)
6.  inconsistent_lighting — highlights on both sides (bad) vs single top-left source (correct)
7.  orphan_pixels       — isolated single pixels scattered (bad) vs clean version (correct)
8.  anti_aliasing       — semi-transparent blended edges (bad) vs crisp 1-px outline (correct)

Public API
----------
generate_all(output_dir) -> list[dict]
    Generate all 16 PNG pairs, return a manifest list.
main()
    CLI entry point — generates to data/antipatterns/labeled/ and writes manifest.json.

Requires: Python 3.14+, Pillow. No numpy / cv2.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw

# Canonical sprite dimensions
W, H = 16, 24

# A small fixed-palette "body silhouette" — foreground / background indicator.
# 1 = inside the sprite body; 0 = transparent / background.
# This 16×24 mask is used as a shared reference shape so all generators
# operate on a recognisable humanoid outline.
_BODY_MASK: list[list[int]] = []


def _build_body_mask() -> list[list[int]]:
    """Return a 16×24 binary mask representing a simple humanoid silhouette."""
    mask = [[0] * W for _ in range(H)]
    # Head: rows 0-5, cols 5-10
    for r in range(0, 6):
        for c in range(5, 11):
            mask[r][c] = 1
    # Neck: rows 6-7, cols 6-9
    for r in range(6, 8):
        for c in range(6, 10):
            mask[r][c] = 1
    # Torso: rows 8-15, cols 3-12
    for r in range(8, 16):
        for c in range(3, 13):
            mask[r][c] = 1
    # Arms: rows 8-14
    for r in range(8, 15):
        mask[r][2] = 1   # left arm
        mask[r][13] = 1  # right arm
    # Legs: rows 16-23
    for r in range(16, 24):
        for c in range(4, 7):
            mask[r][c] = 1   # left leg
        for c in range(9, 12):
            mask[r][c] = 1   # right leg
    return mask


_BODY_MASK = _build_body_mask()

# Background / transparent colour used on both variants
_BG = (0, 0, 0, 0)


def _new_rgba() -> Image.Image:
    """Create a transparent 16×24 RGBA canvas."""
    return Image.new("RGBA", (W, H), _BG)


def _clamp(v: int, lo: int = 0, hi: int = 255) -> int:
    return max(lo, min(hi, v))


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    """Convert HSV (h∈[0,360), s/v∈[0,1]) to integer RGB tuple."""
    h = h % 360
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    if h < 60:
        r, g, b = c, x, 0.0
    elif h < 120:
        r, g, b = x, c, 0.0
    elif h < 180:
        r, g, b = 0.0, c, x
    elif h < 240:
        r, g, b = 0.0, x, c
    elif h < 300:
        r, g, b = x, 0.0, c
    else:
        r, g, b = c, 0.0, x
    return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))


def _darken(r: int, g: int, b: int, factor: float = 0.55) -> tuple[int, int, int]:
    return (_clamp(int(r * factor)), _clamp(int(g * factor)), _clamp(int(b * factor)))


# ---------------------------------------------------------------------------
# 1. pillow_shading
# ---------------------------------------------------------------------------

def _gen_pillow_shading() -> tuple[Image.Image, Image.Image]:
    """Smooth circular gradient (bad) vs flat pixel regions + hue ramp (correct)."""
    base_hue = 200          # steel blue character
    base_r, base_g, base_b = _hsv_to_rgb(base_hue, 0.6, 0.85)

    # --- BAD: radial gradient blended from centre ---
    bad = _new_rgba()
    cx, cy = W / 2, H / 2
    max_dist = math.hypot(cx, cy)
    for row in range(H):
        for col in range(W):
            if not _BODY_MASK[row][col]:
                continue
            dist = math.hypot(col - cx, row - cy)
            t = dist / max_dist            # 0 = centre, 1 = corner
            r = _clamp(int(base_r * (1 - t * 0.7)))
            g = _clamp(int(base_g * (1 - t * 0.7)))
            b = _clamp(int(base_b * (1 - t * 0.7)))
            bad.putpixel((col, row), (r, g, b, 255))

    # --- CORRECT: flat regions with 4-step hue-shifted ramp (top-lit) ---
    good = _new_rgba()
    # Light source: top-left → rows near top get lighter, rows near bottom darker
    steps = [
        (0,    6,  _hsv_to_rgb(base_hue + 10, 0.35, 0.95)),   # highlight
        (6,    12, _hsv_to_rgb(base_hue,       0.55, 0.80)),   # mid-light
        (12,   18, _hsv_to_rgb(base_hue - 5,   0.70, 0.60)),   # mid-shadow
        (18,   H,  _hsv_to_rgb(base_hue - 10,  0.80, 0.40)),   # deep shadow
    ]
    for r_start, r_end, col in steps:
        for row in range(r_start, r_end):
            for c in range(W):
                if _BODY_MASK[row][c]:
                    good.putpixel((c, row), col + (255,))

    return bad, good


# ---------------------------------------------------------------------------
# 2. color_banding
# ---------------------------------------------------------------------------

def _gen_color_banding() -> tuple[Image.Image, Image.Image]:
    """Grey brightness bands, no hue (bad) vs hue-shifted ramp (correct)."""
    # --- BAD: pure greyscale bands ---
    bad = _new_rgba()
    n_bands = 8
    for row in range(H):
        for col in range(W):
            if not _BODY_MASK[row][col]:
                continue
            band = int(row / H * n_bands)
            brightness = 220 - band * 22
            bad.putpixel((col, row), (_clamp(brightness),) * 3 + (255,))

    # --- CORRECT: hue-shifted ramp (warm highlight → cool shadow) ---
    good = _new_rgba()
    for row in range(H):
        for col in range(W):
            if not _BODY_MASK[row][col]:
                continue
            t = row / (H - 1)                        # 0 = top, 1 = bottom
            hue = 45 - t * 60                        # warm yellow → cool blue
            sat = 0.45 + t * 0.35
            val = 0.90 - t * 0.45
            rgb = _hsv_to_rgb(hue % 360, sat, val)
            good.putpixel((col, row), rgb + (255,))

    return bad, good


# ---------------------------------------------------------------------------
# 3. pure_black_outline
# ---------------------------------------------------------------------------

def _gen_pure_black_outline() -> tuple[Image.Image, Image.Image]:
    """#000000 outline (bad) vs darkened local-colour outline (correct)."""
    body_col = _hsv_to_rgb(120, 0.55, 0.75)   # green character

    def _is_edge(row: int, col: int) -> bool:
        """True if (row, col) is a body pixel adjacent to a non-body pixel."""
        if not _BODY_MASK[row][col]:
            return False
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = row + dr, col + dc
            if nr < 0 or nr >= H or nc < 0 or nc >= W or not _BODY_MASK[nr][nc]:
                return True
        return False

    # --- BAD: pure black outline ---
    bad = _new_rgba()
    for row in range(H):
        for col in range(W):
            if not _BODY_MASK[row][col]:
                continue
            if _is_edge(row, col):
                bad.putpixel((col, row), (0, 0, 0, 255))
            else:
                bad.putpixel((col, row), body_col + (255,))

    # --- CORRECT: darkened local-colour outline ---
    outline_col = _darken(*body_col, factor=0.45)
    good = _new_rgba()
    for row in range(H):
        for col in range(W):
            if not _BODY_MASK[row][col]:
                continue
            if _is_edge(row, col):
                good.putpixel((col, row), outline_col + (255,))
            else:
                good.putpixel((col, row), body_col + (255,))

    return bad, good


# ---------------------------------------------------------------------------
# 4. random_dithering
# ---------------------------------------------------------------------------

def _gen_random_dithering() -> tuple[Image.Image, Image.Image]:
    """Random noise pixels (bad) vs structured 2-colour checkerboard (correct)."""
    rng = random.Random(99)
    col_a = _hsv_to_rgb(30, 0.65, 0.90)   # warm light
    col_b = _hsv_to_rgb(30, 0.80, 0.55)   # warm dark

    # --- BAD: random colour per pixel ---
    bad = _new_rgba()
    for row in range(H):
        for col in range(W):
            if not _BODY_MASK[row][col]:
                continue
            noise_r = rng.randint(140, 240)
            noise_g = rng.randint(80, 180)
            noise_b = rng.randint(20, 120)
            bad.putpixel((col, row), (noise_r, noise_g, noise_b, 255))

    # --- CORRECT: ordered checkerboard between two related colours ---
    good = _new_rgba()
    for row in range(H):
        for col in range(W):
            if not _BODY_MASK[row][col]:
                continue
            c = col_a if (row + col) % 2 == 0 else col_b
            good.putpixel((col, row), c + (255,))

    return bad, good


# ---------------------------------------------------------------------------
# 5. palette_bloat
# ---------------------------------------------------------------------------

def _gen_palette_bloat() -> tuple[Image.Image, Image.Image]:
    """20+ distinct colors (bad) vs ≤15 colors via posterisation (correct)."""
    rng = random.Random(7)

    # --- BAD: many random hues, one per pixel-column-group ---
    bad = _new_rgba()
    unique_colors: list[tuple[int, int, int]] = []
    for _ in range(24):
        h = rng.uniform(0, 360)
        s = rng.uniform(0.4, 0.9)
        v = rng.uniform(0.5, 0.9)
        unique_colors.append(_hsv_to_rgb(h, s, v))

    for row in range(H):
        for col in range(W):
            if not _BODY_MASK[row][col]:
                continue
            idx = (row + col) % len(unique_colors)
            bad.putpixel((col, row), unique_colors[idx] + (255,))

    # --- CORRECT: quantise to 15 colours via Pillow's quantize ---
    # Convert to P mode (palette) with 15 colours then back to RGBA.
    bad_rgb = bad.convert("RGB")
    quantised = bad_rgb.quantize(colors=15, method=Image.Quantize.MEDIANCUT)
    good_rgb = quantised.convert("RGB")

    # Re-apply transparency mask
    good = _new_rgba()
    for row in range(H):
        for col in range(W):
            if _BODY_MASK[row][col]:
                good.putpixel((col, row), good_rgb.getpixel((col, row)) + (255,))

    return bad, good


# ---------------------------------------------------------------------------
# 6. inconsistent_lighting
# ---------------------------------------------------------------------------

def _gen_inconsistent_lighting() -> tuple[Image.Image, Image.Image]:
    """Highlights on both left & right sides (bad) vs single top-left source (correct)."""
    base_col = _hsv_to_rgb(260, 0.50, 0.75)   # muted purple
    highlight = _hsv_to_rgb(260, 0.20, 0.95)
    shadow    = _hsv_to_rgb(260, 0.70, 0.40)
    mid       = _hsv_to_rgb(260, 0.50, 0.65)

    # --- BAD: bright edges on both left and right columns ---
    bad = _new_rgba()
    for row in range(H):
        for col in range(W):
            if not _BODY_MASK[row][col]:
                continue
            # Artificially light both left and right edges
            row_fraction = row / H
            if col <= 4 or col >= W - 5:
                c = highlight                    # wrong: both sides lit
            elif col <= 6 or col >= W - 7:
                c = mid
            else:
                c = shadow                       # core is dark for no reason
            bad.putpixel((col, row), c + (255,))

    # --- CORRECT: single top-left light source ---
    good = _new_rgba()
    for row in range(H):
        for col in range(W):
            if not _BODY_MASK[row][col]:
                continue
            # Light comes from top-left: weight by (1 - col/W) * (1 - row/H)
            light = (1 - col / W) * (1 - row / H)
            if light > 0.55:
                c = highlight
            elif light > 0.30:
                c = mid
            elif light > 0.12:
                c = base_col
            else:
                c = shadow
            good.putpixel((col, row), c + (255,))

    return bad, good


# ---------------------------------------------------------------------------
# 7. orphan_pixels
# ---------------------------------------------------------------------------

def _gen_orphan_pixels() -> tuple[Image.Image, Image.Image]:
    """Isolated single pixels (bad) vs clean version (correct)."""
    rng = random.Random(13)
    body_col = _hsv_to_rgb(0, 0.60, 0.80)   # red character

    def _base_img() -> Image.Image:
        img = _new_rgba()
        for row in range(H):
            for col in range(W):
                if _BODY_MASK[row][col]:
                    img.putpixel((col, row), body_col + (255,))
        return img

    # --- CORRECT: plain body ---
    good = _base_img()

    # --- BAD: sprinkle 12 isolated random pixels in transparent background ---
    bad = _base_img()
    placed = 0
    attempts = 0
    while placed < 12 and attempts < 500:
        attempts += 1
        r = rng.randint(0, H - 1)
        c = rng.randint(0, W - 1)
        if _BODY_MASK[r][c]:
            continue
        # Only add if none of the 4 neighbours are also stray pixels
        # (so they stay truly isolated)
        neighbours_clear = all(
            bad.getpixel((_clamp(c + dc, 0, W - 1), _clamp(r + dr, 0, H - 1))) == _BG
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
        )
        if neighbours_clear:
            stray_col = (_clamp(rng.randint(0, 255)),
                         _clamp(rng.randint(0, 255)),
                         _clamp(rng.randint(0, 255)), 255)
            bad.putpixel((c, r), stray_col)
            placed += 1

    return bad, good


# ---------------------------------------------------------------------------
# 8. anti_aliasing
# ---------------------------------------------------------------------------

def _gen_anti_aliasing() -> tuple[Image.Image, Image.Image]:
    """Semi-transparent blended edge pixels (bad) vs crisp 1-px outline (correct)."""
    body_col   = (88, 160, 230, 255)
    outline_col = _darken(88, 160, 230, 0.50) + (255,)

    def _is_edge(row: int, col: int) -> bool:
        if not _BODY_MASK[row][col]:
            return False
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = row + dr, col + dc
            if nr < 0 or nr >= H or nc < 0 or nc >= W or not _BODY_MASK[nr][nc]:
                return True
        return False

    # --- BAD: edge pixels are blended (semi-transparent / grey mixed) ---
    bad = _new_rgba()
    for row in range(H):
        for col in range(W):
            if not _BODY_MASK[row][col]:
                if _is_edge(row, col):
                    # Place blended ghost pixel just outside edge
                    pass
                continue
            if _is_edge(row, col):
                # Blend body colour toward transparent
                blended = (
                    _clamp((body_col[0] + 255) // 2),
                    _clamp((body_col[1] + 255) // 2),
                    _clamp((body_col[2] + 255) // 2),
                    140,   # semi-transparent
                )
                bad.putpixel((col, row), blended)
            else:
                bad.putpixel((col, row), body_col)

    # --- CORRECT: crisp 1-px darkened outline, fully opaque ---
    good = _new_rgba()
    for row in range(H):
        for col in range(W):
            if not _BODY_MASK[row][col]:
                continue
            if _is_edge(row, col):
                good.putpixel((col, row), outline_col)
            else:
                good.putpixel((col, row), body_col)

    return bad, good


# ---------------------------------------------------------------------------
# Public generate_all()
# ---------------------------------------------------------------------------

_GENERATORS: list[tuple[str, callable]] = [
    ("pillow_shading",       _gen_pillow_shading),
    ("color_banding",        _gen_color_banding),
    ("pure_black_outline",   _gen_pure_black_outline),
    ("random_dithering",     _gen_random_dithering),
    ("palette_bloat",        _gen_palette_bloat),
    ("inconsistent_lighting",_gen_inconsistent_lighting),
    ("orphan_pixels",        _gen_orphan_pixels),
    ("anti_aliasing",        _gen_anti_aliasing),
]


def generate_all(output_dir: str | Path) -> list[dict]:
    """Generate all antipattern PNG pairs and write them to *output_dir*.

    For each failure mode a ``<name>_bad.png`` and ``<name>_correct.png`` file
    are written.  Both images are 16 × 24 pixels, RGBA.

    Parameters
    ----------
    output_dir:
        Directory where the PNG pairs are saved.  Created if absent.

    Returns
    -------
    list[dict]
        A manifest list — one entry per failure mode — with keys:

        ``name`` (str), ``bad_path`` (str), ``correct_path`` (str),
        ``width`` (int), ``height`` (int), ``description`` (str).

    Examples
    --------
    ::

        manifest = generate_all("data/antipatterns/labeled/")
        for entry in manifest:
            print(entry["name"], "→", entry["bad_path"])
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    descriptions = {
        "pillow_shading":        "Circular gradient shading (bad) vs flat pixel regions with hue ramp (correct)",
        "color_banding":         "Grey brightness bands without hue shift (bad) vs hue-shifted ramp (correct)",
        "pure_black_outline":    "Pure #000000 outline (bad) vs darkened local-colour outline (correct)",
        "random_dithering":      "Random noise pixels (bad) vs ordered 2-colour checkerboard (correct)",
        "palette_bloat":         "24+ distinct colours (bad) vs ≤15 colour palette (correct)",
        "inconsistent_lighting": "Highlights on both sides (bad) vs single top-left light source (correct)",
        "orphan_pixels":         "Isolated stray pixels in background (bad) vs clean silhouette (correct)",
        "anti_aliasing":         "Semi-transparent blended edge pixels (bad) vs crisp 1-px outline (correct)",
    }

    manifest: list[dict] = []
    for name, generator_fn in _GENERATORS:
        bad_img, good_img = generator_fn()
        bad_path  = output_dir / f"{name}_bad.png"
        good_path = output_dir / f"{name}_correct.png"
        bad_img.save(bad_path,  "PNG")
        good_img.save(good_path, "PNG")

        manifest.append({
            "name":         name,
            "bad_path":     str(bad_path),
            "correct_path": str(good_path),
            "width":        W,
            "height":       H,
            "description":  descriptions[name],
        })

    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """Command-line entry point.

    Generates all antipattern PNG pairs to the target output directory and
    writes a ``manifest.json`` alongside them.

    Arguments
    ---------
    --output-dir
        Destination directory.  Defaults to ``data/antipatterns/labeled/``
        relative to the current working directory.

    Example
    -------
    ::

        python generator.py
        python generator.py --output-dir /tmp/antipatterns/
    """
    parser = argparse.ArgumentParser(
        prog="generator",
        description="AM Pixel — antipattern sprite pair generator",
    )
    parser.add_argument(
        "--output-dir",
        default="data/antipatterns/labeled/",
        help="Output directory for PNG pairs and manifest.json (default: data/antipatterns/labeled/)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    print(f"[generator] Generating antipattern pairs → {output_dir}")
    manifest = generate_all(output_dir)

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[generator] Wrote {len(manifest)} pairs + manifest → {manifest_path}")
    for entry in manifest:
        print(f"  [{entry['name']}]")
        print(f"    bad     : {entry['bad_path']}")
        print(f"    correct : {entry['correct_path']}")


if __name__ == "__main__":
    main()
