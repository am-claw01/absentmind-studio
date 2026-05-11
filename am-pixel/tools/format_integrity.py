#!/usr/bin/env python3.14
"""
tools/format_integrity.py
==========================
CHANGE-033 — Format Integrity Detection and Provenance

Two modes:
  1. SCAN mode (default / --dry-run): read every sprite_XXXX.json in corpus,
     detect JPEG-contaminated PNGs by color count vs resolution bound,
     report suspect counts by pack — no writes.

  2. APPLY mode (--apply): write format_provenance fields into every
     sprite_XXXX.json, move format_suspect sprites to quarantine.

Color count upper bounds (conservative — allows complex pixel art):
  sprite area ≤ 256 px  (≤16×16):  max 64  unique non-transparent colors
  sprite area ≤ 4096 px (≤64×64):  max 128 unique non-transparent colors
  sprite area >  4096 px:          no upper bound (large sprites allowed more)

Writes four fields into sprite_XXXX.json under "format_provenance":
  file_format             : "png"
  native_format           : "png_native" | "png_from_jpeg_suspected" | "unknown"
  color_count_at_ingestion: int
  palette_indexed         : bool

Usage:
  python tools/format_integrity.py [--corpus data/corpus/train] [--dry-run]
  python tools/format_integrity.py [--corpus data/corpus/train] --apply
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
REVIEW_DIR   = PROJECT_ROOT / "data" / "golden_review"
QUARANTINE   = PROJECT_ROOT / "data" / "quarantine" / "format_suspect"
QMANIFEST    = PROJECT_ROOT / "data" / "quarantine" / "quarantine_manifest.jsonl"
FLAG_PACK_RATE = 0.20   # packs above this format_suspect rate are flagged

# Color count upper bounds by pixel area
AREA_BOUNDS = [
    (256,  64),   # ≤16×16 → max 64 unique colors
    (4096, 128),  # ≤64×64 → max 128 unique colors
]


def color_bound(width: int, height: int) -> int | None:
    """Return the max expected unique color count for this resolution, or None if no bound."""
    area = width * height
    for max_area, max_colors in AREA_BOUNDS:
        if area <= max_area:
            return max_colors
    return None  # large sprites — no upper bound


def get_palette_indexed(png_path: Path) -> bool:
    """Return True if PNG uses palette-indexed mode (mode 'P')."""
    if not HAS_PIL or not png_path.exists():
        return False
    try:
        with Image.open(png_path) as img:
            return img.mode == "P"
    except Exception:
        return False


def check_format(meta: dict, png_path: Path) -> dict:
    """
    Compute format_provenance dict for a sprite.
    Uses index_grid + transparent_index from metadata for color count
    (avoids opening the PNG for the count — metadata already has this).
    Falls back to PNG pixel scan if index_grid absent and PIL available.
    """
    width         = meta.get("width", 0)
    height        = meta.get("height", 0)
    index_grid    = meta.get("index_grid", [])
    transparent_i = meta.get("transparent_index", None)
    palette       = meta.get("palette", [])

    # Compute unique non-transparent color count from metadata
    if index_grid:
        used = set(index_grid)
        if transparent_i is not None:
            used.discard(transparent_i)
        color_count = len(used)
    elif palette:
        color_count = len(palette)
    elif HAS_PIL and png_path.exists():
        try:
            with Image.open(png_path) as img:
                rgba = img.convert("RGBA")
                pixels = set(rgba.getdata())
                color_count = len({p for p in pixels if p[3] > 0})
        except Exception:
            color_count = -1
    else:
        color_count = -1

    # Determine native_format
    bound = color_bound(width, height)
    if color_count < 0:
        native_format = "unknown"
    elif bound is not None and color_count > bound:
        native_format = "png_from_jpeg_suspected"
    else:
        native_format = "png_native"

    palette_indexed = get_palette_indexed(png_path)

    return {
        "file_format":              "png",
        "native_format":            native_format,
        "color_count_at_ingestion": color_count,
        "palette_indexed":          palette_indexed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="CHANGE-033 format integrity pass")
    parser.add_argument("--corpus",  default=str(PROJECT_ROOT / "data" / "corpus" / "train"))
    parser.add_argument("--apply",   action="store_true",
                        help="Write format_provenance fields and quarantine suspects. "
                             "Default (omit) is dry-run scan only.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Alias for default scan-only mode (no writes)")
    args = parser.parse_args()
    dry_run = not args.apply

    corpus_dir = Path(args.corpus)
    if not corpus_dir.exists():
        print(f"ERROR: corpus not found: {corpus_dir}", file=sys.stderr)
        sys.exit(1)

    if not dry_run:
        QUARANTINE.mkdir(parents=True, exist_ok=True)
        QMANIFEST.parent.mkdir(parents=True, exist_ok=True)

    # Collect sprite JSON files
    print("Scanning corpus for sprite metadata...", flush=True)
    json_files: list[Path] = []
    for root, dirs, files in os.walk(corpus_dir):
        dirs.sort()
        for fname in sorted(files):
            if (fname.endswith(".json")
                    and not fname.endswith("_seq.json")
                    and fname not in ("manifest.json", "tileset_meta.json")):
                json_files.append(Path(root) / fname)

    total = len(json_files)
    print(f"Found {total:,} sprite metadata files", flush=True)

    suspect_count  = 0
    already_tagged = 0
    written        = 0
    pack_total:   Counter = Counter()
    pack_suspect: Counter = Counter()
    report_every = 10_000

    qmanifest_fh = None
    if not dry_run:
        qmanifest_fh = open(QMANIFEST, "a", encoding="utf-8")

    for i, json_path in enumerate(json_files, 1):
        try:
            pack_name = json_path.relative_to(corpus_dir).parts[0]
        except (ValueError, IndexError):
            pack_name = json_path.parent.name

        pack_total[pack_name] += 1

        try:
            meta = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Skip if already tagged (idempotent)
        if "format_provenance" in meta:
            already_tagged += 1
            fp = meta["format_provenance"]
            if fp.get("native_format") == "png_from_jpeg_suspected":
                pack_suspect[pack_name] += 1
                suspect_count += 1
            if i % report_every == 0:
                print(f"  {i:,}/{total:,} processed...", flush=True)
            continue

        png_path = json_path.with_suffix(".png")
        fp = check_format(meta, png_path)

        if fp["native_format"] == "png_from_jpeg_suspected":
            pack_suspect[pack_name] += 1
            suspect_count += 1

            if not dry_run:
                # Quarantine: move .png + .json + _seq.json
                seq_path  = json_path.parent / f"{json_path.stem}_seq.json"
                dest_dir  = QUARANTINE / pack_name / json_path.parent.name
                dest_dir.mkdir(parents=True, exist_ok=True)
                for f in (png_path, json_path, seq_path):
                    if f.exists():
                        f.rename(dest_dir / f.name)
                entry = {
                    "sprite_json":       str(json_path.relative_to(PROJECT_ROOT)),
                    "pack_name":         pack_name,
                    "sheet_dir":         json_path.parent.name,
                    "quarantine_category": "format_suspect",
                    "quarantine_dir":    str(QUARANTINE.relative_to(PROJECT_ROOT)),
                    "quarantine_reason": (
                        f"Color count {fp['color_count_at_ingestion']} exceeds bound "
                        f"for {meta.get('width',0)}x{meta.get('height',0)} sprite — "
                        "suspected JPEG-contaminated PNG or misclassified photograph."
                    ),
                    "quarantined_at": datetime.datetime.utcnow().isoformat(),
                }
                if qmanifest_fh:
                    qmanifest_fh.write(json.dumps(entry) + "\n")
                    qmanifest_fh.flush()
        else:
            # Write format_provenance into metadata JSON
            if not dry_run and json_path.exists():
                meta["format_provenance"] = fp
                json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
                written += 1

        if i % report_every == 0:
            print(f"  {i:,}/{total:,} processed — {suspect_count:,} suspects so far...", flush=True)

    if qmanifest_fh:
        qmanifest_fh.close()

    # --- Report ---
    print("\n" + "=" * 60)
    print("FORMAT INTEGRITY REPORT")
    print("=" * 60)
    print(f"  Total sprites scanned       : {total:,}")
    print(f"  Already tagged (skipped)    : {already_tagged:,}")
    print(f"  format_provenance written   : {written:,}" if not dry_run else "  (dry-run — no writes)")
    print(f"  format_suspect quarantined  : {suspect_count:,}  ({suspect_count/total:.1%})")
    if dry_run:
        print("  *** DRY-RUN — no files moved or written ***")

    flagged_packs = {
        p: (pack_suspect[p], pack_total[p], pack_suspect[p] / pack_total[p])
        for p in pack_total
        if pack_total[p] > 0 and pack_suspect.get(p, 0) / pack_total[p] > FLAG_PACK_RATE
    }
    if flagged_packs:
        print(f"\n⚠  FLAGGED PACKS (>{ FLAG_PACK_RATE:.0%} format_suspect — human review required):")
        for pack, (sus, tot, rate) in sorted(flagged_packs.items(), key=lambda x: -x[1][2]):
            print(f"  {pack:<60}  {sus:>5,}/{tot:<5,}  ({rate:.1%})")
    else:
        print(f"\n  No packs above {FLAG_PACK_RATE:.0%} format_suspect rate")

    print("=" * 60)


# ── Public API for use by run_pipeline.py / harvest_loop.py at ingestion ───

def compute_format_provenance(meta: dict, png_path: Path) -> dict:
    """
    Compute and return the format_provenance dict for a sprite at ingestion time.
    Call this in run_pipeline.py / harvest_loop.py when writing sprite_XXXX.json.
    """
    return check_format(meta, png_path)


def is_format_suspect(fp: dict) -> bool:
    """Return True if the format_provenance dict indicates JPEG contamination."""
    return fp.get("native_format") == "png_from_jpeg_suspected"


if __name__ == "__main__":
    main()
