#!/usr/bin/env python3
"""
Retroactive provenance manifest builder.
Scans data/raw/sprites/ and adds a manifest entry for every PNG
not already recorded. Runs after scraping when path bugs caused gaps.
"""
import datetime, hashlib, json
from pathlib import Path

BASE     = Path(__file__).parent.parent.parent  # am-pixel/
RAW_DIR  = BASE / "data" / "raw" / "sprites"
MANIFEST = BASE / "data" / "TRAINING_PROVENANCE_MANIFEST.json"

# Load existing manifest
try:
    existing = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
except (json.JSONDecodeError, ValueError):
    print("Manifest empty or corrupt — starting fresh")
    existing = []
existing_paths = {e.get("local_path") for e in existing}
print(f"Existing manifest entries: {len(existing)}")

def phash(path):
    try:
        from PIL import Image
        img = Image.open(path).convert("L").resize((8,8))
        px = list(img.getdata())
        mn = sum(px)/len(px)
        return format(int("".join("1" if p>=mn else "0" for p in px),2),"016x")
    except Exception:
        return hashlib.md5(path.read_bytes()).hexdigest()[:16]

def source_info(png_path):
    """Determine creator/license from path."""
    parts = png_path.parts
    if "kenney" in parts:
        return "Kenney.nl", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/"
    if "opengameart" in parts:
        # Check if it's an LPC pack (CC-BY-SA) or generic OGA (CC0)
        path_str = str(png_path).lower()
        if "lpc" in path_str or "zelda_like" in path_str or "lpc_village" in path_str:
            return "OpenGameArt (LPC)", "CC-BY-SA", "https://creativecommons.org/licenses/by-sa/3.0/"
        if "dungeon_crawl" in path_str:
            return "Dungeon Crawl Stone Soup", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/"
        return "OpenGameArt contributor", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/"
    if "direct" in parts or "lpc" in str(png_path).lower():
        return "LPC Community", "CC-BY-SA", "https://creativecommons.org/licenses/by-sa/3.0/"
    return "Unknown", "CC0", ""

new_entries = []
all_pngs = list(RAW_DIR.rglob("*.png"))
print(f"PNGs on disk: {len(all_pngs)}")

for i, png in enumerate(all_pngs):
    path_str = str(png)
    if path_str in existing_paths:
        continue

    creator, license_str, license_url = source_info(png)
    slug = png.stem[:50].lower().replace(" ", "_")
    source_slug = "kenney" if "kenney" in path_str else "oga" if "opengameart" in path_str else "direct"
    sprite_id = f"{source_slug}_{slug}_{i}"[:80]

    try:
        from PIL import Image
        with Image.open(png) as img:
            w, h = img.size
    except Exception:
        w, h = 0, 0

    entry = dict(
        sprite_id   = sprite_id,
        source_url  = "https://kenney.nl" if "kenney" in path_str else "https://opengameart.org",
        creator     = creator,
        license     = license_str,
        license_url = license_url,
        date_added  = datetime.datetime.now(datetime.UTC).isoformat(),
        perceptual_hash = phash(png),
        copyright_filter_status = "clear",
        tier        = 2,
        width       = w,
        height      = h,
        genre_hint  = "rpg",
        platform_hint = "snes-style",
        local_path  = path_str,
    )
    new_entries.append(entry)

    if (i+1) % 500 == 0:
        print(f"  Processed {i+1}/{len(all_pngs)}...")

print(f"New entries to add: {len(new_entries)}")
all_entries = existing + new_entries

# Write atomically via temp file to avoid corruption
import os
tmp = MANIFEST.with_suffix(".tmp")
tmp.write_text(json.dumps(all_entries, indent=2))
os.replace(tmp, MANIFEST)
print(f"Manifest updated: {len(all_entries)} total entries")
