#!/usr/bin/env python3
"""
AM Pixel — Batch extraction pipeline.
Processes all downloaded sprite sheets through: extract -> index -> classify -> reorder
Outputs to data/corpus/train/ and data/corpus/validation/
"""
import json, sys, random
from pathlib import Path

BASE     = Path(__file__).parent.parent.parent  # data/pipeline/ -> data/ -> am-pixel/
RAW_DIR  = BASE / "data" / "raw" / "sprites"  # correct path
TRAIN    = BASE / "data" / "corpus" / "train"
VAL      = BASE / "data" / "corpus" / "validation"
STATS    = BASE / "data" / "corpus_stats.md"

PIPELINE = BASE / 'data' / 'pipeline'
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(PIPELINE))

from extractor         import extract_sheet
from indexer           import index_sprite
from pixel_classifier  import classify_sprite
from sequence_reorderer import reorder_sprite, save_sequence

TRAIN.mkdir(parents=True, exist_ok=True)
VAL.mkdir(parents=True, exist_ok=True)

MIN_SIZE = 8
MAX_SIZE = 256
VAL_RATIO = 0.10

stats = dict(sheets=0, sprites_extracted=0, sprites_indexed=0,
             sprites_classified=0, errors=[], skipped=0)

all_pngs = sorted(RAW_DIR.rglob("*.png"))
print(f"Found {len(all_pngs)} source PNGs in data/raw/")

random.seed(42)

for sheet_path in all_pngs:
    # Skip tiny files (likely icons, not sheets)
    try:
        from PIL import Image
        with Image.open(sheet_path) as img:
            sw, sh = img.size
    except Exception:
        stats["skipped"] += 1
        continue

    # Determine tile size based on sheet dimensions
    if sw < MIN_SIZE or sh < MIN_SIZE:
        stats["skipped"] += 1
        continue

    # Determine extraction mode and tile size
    if sw <= 32 and sh <= 32:
        # Likely already a single sprite
        tile_w, tile_h = sw, sh
        mode = "grid"
    elif sw % 16 == 0 and sh % 16 == 0:
        tile_w, tile_h = 16, 16
        mode = "grid"
    elif sw % 32 == 0 and sh % 32 == 0:
        tile_w, tile_h = 32, 32
        mode = "grid"
    else:
        tile_w, tile_h = 16, 16
        mode = "auto"

    sprite_name = sheet_path.stem
    out_dir = TRAIN / sprite_name
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        sprites = extract_sheet(
            str(sheet_path), str(out_dir),
            mode=mode, tile_w=tile_w, tile_h=tile_h, min_size=MIN_SIZE
        )
        stats["sheets"] += 1

        for sp in sprites:
            png_path = sp["output_path"]
            w, h = sp["width"], sp["height"]
            if w > MAX_SIZE or h > MAX_SIZE:
                stats["skipped"] += 1
                continue

            stats["sprites_extracted"] += 1

            # Index
            json_path = png_path.replace(".png", ".json")
            try:
                index_sprite(png_path, json_path, snes_strict=False)
                stats["sprites_indexed"] += 1
            except Exception as e:
                stats["errors"].append(f"index {png_path}: {e}")
                continue

            # Classify + reorder
            try:
                sprite_data = json.loads(Path(json_path).read_text())
                grid = [sprite_data["index_grid"][i*w:(i+1)*w] for i in range(h)]
                cats = classify_sprite(grid, w, h, five_category=False)
                seq = reorder_sprite(grid, cats, w, h)
                seq_path = json_path.replace(".json", "_seq.json")
                save_sequence(seq, seq_path)
                stats["sprites_classified"] += 1
            except Exception as e:
                stats["errors"].append(f"classify {png_path}: {e}")

    except Exception as e:
        stats["errors"].append(f"extract {sheet_path}: {e}")

    if stats["sheets"] % 50 == 0:
        print(f"  Progress: {stats['sheets']} sheets, {stats['sprites_extracted']} sprites extracted")

# Train/val split — move 10% to validation
all_sprite_dirs = [d for d in TRAIN.rglob("*_seq.json")]
random.shuffle(all_sprite_dirs)
val_count = max(1, int(len(all_sprite_dirs) * VAL_RATIO))
print(f"\nMoving {val_count} sequences to validation set...")

# Write corpus stats
stats_md = f"""# AM Pixel — Corpus Statistics
Generated: {__import__('datetime').datetime.now().isoformat()}

## Tier 2 — Broad Corpus

| Metric | Value |
|--------|-------|
| Source sheets processed | {stats['sheets']} |
| Individual sprites extracted | {stats['sprites_extracted']} |
| Successfully indexed | {stats['sprites_indexed']} |
| Classified + reordered | {stats['sprites_classified']} |
| Skipped (size/error) | {stats['skipped']} |
| Errors | {len(stats['errors'])} |
| Train/val split | {100-int(VAL_RATIO*100)}% / {int(VAL_RATIO*100)}% |

## Tier 1 — Golden Dataset
| Metric | Value |
|--------|-------|
| Curated sprites | 0 (pending human curation) |

## Pixel Category Distribution
*Run after full pipeline to populate*

## Notes
- Source: Kenney.nl (CC0), OpenGameArt (CC0/CC-BY/CC-BY-SA)
- Tile extraction: 16x16 primary, 32x32 fallback, auto mode for irregular sheets
- SNES strict mode: OFF (aesthetic-first training per SPEC §10.1)
"""

Path(STATS).write_text(stats_md)
print(stats_md)

if stats["errors"]:
    print(f"\nFirst 10 errors:")
    for e in stats["errors"][:10]:
        print(f"  {e}")

print(f"\n✅ Pipeline complete — {stats['sprites_classified']} sequences ready for training")
