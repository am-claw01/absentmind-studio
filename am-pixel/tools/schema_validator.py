#!/usr/bin/env python3.14
"""
tools/schema_validator.py
==========================
CHANGE-034 — Schema Validation Pass

Walks every sprite_XXXX.json in data/corpus/train/ and verifies that all
required schema fields are present. Missing fields are an error condition.
Null and 'unknown' are valid values — absence is not.

Required fields (post CHANGE-033 + CHANGE-034):
  From indexer:     sprite_id, width, height, palette, index_grid, transparent_index
  CHANGE-033:       format_provenance.file_format, .native_format,
                    .color_count_at_ingestion, .palette_indexed
  CHANGE-034:       sprite_class, sprite_subclass, class_confidence, class_rule_matched,
                    aesthetic_style, aesthetic_subclass,
                    animation_id, frame_index, frame_count, animation_type,
                    pose_direction, view_angle,
                    rubric_score, rubric_bucket, perceptual_hash

Usage:
  python tools/schema_validator.py [--corpus data/corpus/train]
  Exit code 0 = all valid. Exit code 1 = schema violations found.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Required top-level fields
REQUIRED_TOP = [
    "sprite_id", "width", "height", "palette", "index_grid", "transparent_index",
    # CHANGE-034
    "sprite_class", "sprite_subclass", "class_confidence", "class_rule_matched",
    "aesthetic_style", "aesthetic_subclass",
    "animation_id", "frame_index", "frame_count", "animation_type",
    "pose_direction", "view_angle",
    "rubric_score", "rubric_bucket", "perceptual_hash",
]

# Required sub-fields inside format_provenance block
REQUIRED_FORMAT_PROVENANCE = [
    "file_format", "native_format", "color_count_at_ingestion", "palette_indexed",
]


def validate_sprite(meta: dict) -> list[str]:
    """Return list of missing field paths. Empty = valid."""
    missing = []
    for field in REQUIRED_TOP:
        if field not in meta:
            missing.append(field)
    fp = meta.get("format_provenance")
    if fp is None:
        missing.append("format_provenance")
    else:
        for sub in REQUIRED_FORMAT_PROVENANCE:
            if sub not in fp:
                missing.append(f"format_provenance.{sub}")
    return missing


def main() -> None:
    parser = argparse.ArgumentParser(description="Schema validation pass — all fields present")
    parser.add_argument("--corpus", default=str(PROJECT_ROOT / "data" / "corpus" / "train"))
    parser.add_argument("--limit", type=int, default=0, help="Stop after N violations (0=all)")
    args = parser.parse_args()

    corpus_dir = Path(args.corpus)
    if not corpus_dir.exists():
        print(f"ERROR: corpus not found: {corpus_dir}", file=sys.stderr)
        sys.exit(1)

    print("Running schema validation pass...", flush=True)
    json_files: list[Path] = []
    for root, dirs, files in os.walk(corpus_dir):
        dirs.sort()
        for fname in sorted(files):
            if (fname.endswith(".json")
                    and not fname.endswith("_seq.json")
                    and fname not in ("manifest.json", "tileset_meta.json")):
                json_files.append(Path(root) / fname)

    total        = len(json_files)
    valid        = 0
    violations   = 0
    field_gaps:  Counter = Counter()
    pack_gaps:   Counter = Counter()
    report_every = 10_000

    for i, json_path in enumerate(json_files, 1):
        try:
            pack_name = json_path.relative_to(corpus_dir).parts[0]
        except (ValueError, IndexError):
            pack_name = json_path.parent.name

        try:
            meta = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            violations += 1
            field_gaps["unreadable_json"] += 1
            pack_gaps[pack_name] += 1
            if args.limit and violations >= args.limit:
                break
            continue

        missing = validate_sprite(meta)
        if missing:
            violations += 1
            pack_gaps[pack_name] += 1
            for f in missing:
                field_gaps[f] += 1
            if args.limit and violations >= args.limit:
                break
        else:
            valid += 1

        if i % report_every == 0:
            print(f"  {i:,}/{total:,} validated — {violations:,} violations so far...", flush=True)

    print("\n" + "=" * 60)
    print("SCHEMA VALIDATION REPORT")
    print("=" * 60)
    print(f"  Total sprites checked   : {total:,}")
    print(f"  Fully valid             : {valid:,}")
    print(f"  Schema violations       : {violations:,}")

    if violations == 0:
        print("\n  ✅ PASS — all sprites have complete schema")
    else:
        print(f"\n  ❌ FAIL — {violations:,} sprites missing required fields")
        print("\nMissing fields (by frequency):")
        for field, count in field_gaps.most_common(20):
            print(f"  {field:<45}  {count:>7,}")
        print("\nTop packs with violations:")
        for pack, count in pack_gaps.most_common(10):
            print(f"  {pack:<60}  {count:>7,}")

    print("=" * 60)
    sys.exit(0 if violations == 0 else 1)


if __name__ == "__main__":
    main()
