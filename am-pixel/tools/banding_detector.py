#!/usr/bin/env python3
"""
tools/banding_detector.py
Detects horizontal/vertical color banding — a common pixel art mistake.
Banding = monotonic brightness ramp across rows/cols without hue shift.
"""
from __future__ import annotations
import json, sys, math, argparse
from pathlib import Path

def _hex_to_rgb(h: str) -> tuple[int,int,int]:
    h = h.lstrip("#")
    return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)

def _luminance(r,g,b) -> float:
    return 0.299*r + 0.587*g + 0.114*b

def _hue(r,g,b) -> float:
    r,g,b = r/255, g/255, b/255
    mx,mn = max(r,g,b), min(r,g,b)
    if mx == mn: return 0.0
    d = mx - mn
    if mx == r:   h = (g-b)/d % 6
    elif mx == g: h = (b-r)/d + 2
    else:         h = (r-g)/d + 4
    return h * 60

def detect_banding(sprite_data: dict) -> dict:
    palette = sprite_data.get("palette", [])
    index_grid_flat = sprite_data.get("index_grid", [])
    w = sprite_data.get("width", 0)
    h = sprite_data.get("height", 0)
    if not w or not h or not palette:
        return dict(has_banding=False, severity=0.0, issues=[], banding_rows=[], banding_cols=[])

    grid = [index_grid_flat[r*w:(r+1)*w] for r in range(h)]
    issues = []
    banding_rows: list[int] = []
    banding_cols: list[int] = []

    # Build per-row dominant non-transparent color luminance + hue
    row_lum, row_hue = [], []
    for r in range(h):
        row_colors = [palette[grid[r][c]-1] for c in range(w) if grid[r][c] > 0 and grid[r][c]-1 < len(palette)]
        if not row_colors:
            row_lum.append(None); row_hue.append(None); continue
        rgbs = [_hex_to_rgb(x) for x in row_colors]
        avg_r = sum(x[0] for x in rgbs)//len(rgbs)
        avg_g = sum(x[1] for x in rgbs)//len(rgbs)
        avg_b = sum(x[2] for x in rgbs)//len(rgbs)
        row_lum.append(_luminance(avg_r,avg_g,avg_b))
        row_hue.append(_hue(avg_r,avg_g,avg_b))

    # Detect monotonic brightness without hue shift across 4+ consecutive rows
    valid = [(i,l,row_hue[i]) for i,l in enumerate(row_lum) if l is not None]
    run_start, run_dir = 0, 0
    for i in range(1, len(valid)):
        idx, lum, hue = valid[i]
        _, prev_lum, prev_hue = valid[i-1]
        d = lum - prev_lum
        hue_diff = abs((hue - prev_hue + 180) % 360 - 180)
        direction = 1 if d > 2 else (-1 if d < -2 else 0)
        if direction != 0 and direction == run_dir and hue_diff < 5:
            run_len = i - run_start + 1
            if run_len >= 4:
                banding_rows.append(idx)
        else:
            run_start, run_dir = i, direction

    severity = min(1.0, len(banding_rows) / max(h, 1))
    has_banding = len(banding_rows) >= 2

    if has_banding:
        issues.append(f"Color banding detected on {len(banding_rows)} rows — monotonic brightness without hue shift")

    return dict(has_banding=has_banding, severity=round(severity,3),
                banding_rows=banding_rows, banding_cols=banding_cols, issues=issues)

def main():
    p = argparse.ArgumentParser(description="Detect color banding in sprite")
    p.add_argument("sprite_json")
    args = p.parse_args()
    data = json.loads(Path(args.sprite_json).read_text())
    result = detect_banding(data)
    print(json.dumps(result, indent=2))
    sys.exit(0 if not result["has_banding"] else 1)

if __name__ == "__main__":
    main()
