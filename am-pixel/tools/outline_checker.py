#!/usr/bin/env python3
"""
tools/outline_checker.py
Identifies pure black outlines — must be darkened local color, not #000000.
"""
from __future__ import annotations
import json, sys, argparse
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("pip install Pillow")

BLACK_THRESHOLD = 20  # channels all below this = "pure black"

def _is_pure_black(r,g,b, threshold=BLACK_THRESHOLD) -> bool:
    return r < threshold and g < threshold and b < threshold

def _is_transparent(a: int) -> bool:
    return a < 10

def _is_outline_pixel(img_data, x, y, w, h) -> bool:
    """Non-transparent pixel adjacent to at least one transparent pixel."""
    r,g,b,a = img_data[y][x]
    if _is_transparent(a):
        return False
    for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
        nx,ny = x+dx, y+dy
        if 0 <= nx < w and 0 <= ny < h:
            _,_,_,na = img_data[ny][nx]
            if _is_transparent(na):
                return True
        else:
            return True  # edge of sprite = outline
    return False

def check_outline_colors(png_path: str) -> dict:
    img = Image.open(png_path).convert("RGBA")
    w, h = img.size
    pixels = [[img.getpixel((x,y)) for x in range(w)] for y in range(h)]

    outline_colors: set[str] = set()
    pure_black_pixels: list[tuple[int,int]] = []

    for y in range(h):
        for x in range(w):
            if _is_outline_pixel(pixels, x, y, w, h):
                r,g,b,_ = pixels[y][x]
                hex_col = f"#{r:02x}{g:02x}{b:02x}"
                outline_colors.add(hex_col)
                if _is_pure_black(r,g,b):
                    pure_black_pixels.append((x,y))

    has_black = len(pure_black_pixels) > 0
    issues = []
    if has_black:
        issues.append(f"Pure black outline on {len(pure_black_pixels)} pixels — use darkened local color instead")

    return dict(
        has_pure_black_outline = has_black,
        outline_colors = sorted(outline_colors),
        pure_black_pixel_count = len(pure_black_pixels),
        pure_black_pixels = pure_black_pixels[:20],  # first 20
        issues = issues,
    )

def score_outline(result: dict) -> float:
    """1.0 = no pure black outlines, 0.0 = all outline pixels are black."""
    if not result.get("outline_colors"):
        return 1.0
    total_outline = result.get("pure_black_pixel_count", 0)
    if total_outline == 0:
        return 1.0
    # Penalize proportionally
    return max(0.0, 1.0 - min(1.0, total_outline / 50))

def main():
    p = argparse.ArgumentParser(description="Check for pure black outlines in sprite PNG")
    p.add_argument("png_path")
    args = p.parse_args()
    result = check_outline_colors(args.png_path)
    result["score"] = score_outline(result)
    print(json.dumps(result, indent=2))
    sys.exit(0 if not result["has_pure_black_outline"] else 1)

if __name__ == "__main__":
    main()
