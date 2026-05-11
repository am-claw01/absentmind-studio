#!/usr/bin/env python3.14
"""
tools/clean_corpus.py
======================
Corpus cleaning pass — removes grid-slicing artifacts from data/corpus/train/
and quarantines non-sprite asset packs before scoring or training.

QUARANTINE (entire pack moved, never deleted):
  texture-*        → data/quarantine/texture_packs/   (uniform-color texture tiles)
  ui_elements      → data/quarantine/ui_elements/     (single-sprite Kenney UI icons)
  monochrome_packs → data/quarantine/monochrome_packs/ (1-bit / intentional monochrome)
  outline_art      → data/quarantine/outline_art/     (outline-only sprites)

ARTIFACT DELETION (all 3 files together — .png + .json + _seq.json):
  1. unique_colors < 2   — truly monochrome (2-color outline+fill sprites are VALID)
  2. entropy       < 0.5 — near-zero pixel entropy from palette distribution
  3. transparency  > 0.80 — >80% transparent pixels (empty tile)
  4. aspect_ratio  > 4.0 or < 0.25 — extreme sliver

Usage:
  python tools/clean_corpus.py [--corpus data/corpus/train] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
REVIEW_DIR   = PROJECT_ROOT / "data" / "golden_review"
QUARANTINE   = PROJECT_ROOT / "data" / "quarantine"
LOG_PATH     = REVIEW_DIR  / "corpus_cleaning_log.jsonl"
QMANIFEST    = QUARANTINE  / "quarantine_manifest.jsonl"
FLAG_RATE    = 0.50


# ---------------------------------------------------------------------------
# Pack classification — quarantine rules
# ---------------------------------------------------------------------------

def _q_texture(p: str) -> bool:
    return p.startswith("texture-") or p.startswith("texture_")

def _q_monochrome(p: str) -> bool:
    """1-bit / intentional monochrome packs and small dark-palette character packs."""
    pl = p.lower()
    if "1-bit-pack" in pl:
        return True
    if "monochrome" in pl and "kenney" in pl:
        return True
    if pl in ("colored-transparent", "colored-transparent_packed",
              "monochrome-transparent", "monochrome-transparent_packed"):
        return True
    if "micro-roguelike" in pl and ("monochrome" in pl or "colored" in pl):
        return True
    # Small character sprite packs: blackMan8, blondeWoman2, greyMan8, etc.
    if re.search(r"(black|blonde|brown1|brown2|grey|red)(man|woman)\d", pl):
        return True
    return False

def _q_outline(p: str) -> bool:
    pl = p.lower()
    return "_outline" in pl or pl.endswith("outline")

# Ordered list: (category_key, dest_subdir, classifier_fn, manifest_note)
QUARANTINE_CATEGORIES = [
    (
        "texture_packs",
        "texture_packs",
        _q_texture,
        "Texture tiles — uniform color distribution, not character sprites, "
        "potentially useful for future texture generation track.",
    ),
    (
        "monochrome_packs",
        "monochrome_packs",
        _q_monochrome,
        "Intentional 1-bit/monochrome art — valid pixel art style, preserved for "
        "potential monochrome generation track. Not deleted because unique_colors < 2 "
        "cannot distinguish intentional monochrome from slicing artifacts.",
    ),
    (
        "outline_art",
        "outline_art",
        _q_outline,
        "Outline-only sprites — intentional art style, valid for outline generation "
        "training. Not deleted because low color count reflects style, not artifact.",
    ),
]
# UI elements = single-sprite packs (identified after pack-count pass)
UI_NOTE = (
    "Kenney UI elements — buttons, icons, arrows — not sprite art, "
    "potentially useful for future UI generation track."
)


# ---------------------------------------------------------------------------
# Artifact checks  (thresholds per user decision 2026-05-10)
# ---------------------------------------------------------------------------

def compute_entropy(counts: dict) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    ent = 0.0
    for v in counts.values():
        if v > 0:
            p = v / total
            ent -= p * math.log2(p)
    return ent


def check_artifact(meta: dict) -> tuple[bool, str, dict]:
    """
    Returns (is_artifact, reason, metrics).
    Sprite metadata format:
      palette        — list of hex strings
      index_grid     — flat list of palette indices
      transparent_index — int index that maps to transparent (may be absent)
      width, height  — int
    """
    metrics: dict = {}

    width         = meta.get("width",  0)
    height        = meta.get("height", 0)
    index_grid    = meta.get("index_grid", [])
    transparent_i = meta.get("transparent_index", None)
    palette       = meta.get("palette", [])

    total_px = len(index_grid) if index_grid else (width * height)

    # --- transparency ratio ---
    if total_px > 0 and transparent_i is not None:
        trans_px    = sum(1 for idx in index_grid if idx == transparent_i)
        trans_ratio = trans_px / total_px
    else:
        trans_ratio = 0.0
    metrics["transparency_ratio"] = round(trans_ratio, 4)

    if trans_ratio > 0.80:
        return True, "transparency_ratio>0.80", metrics

    # --- unique non-transparent palette indices ---
    if index_grid:
        used = set(index_grid)
        if transparent_i is not None:
            used.discard(transparent_i)
        unique_colors = len(used)
    else:
        unique_colors = len(palette)
    metrics["unique_colors"] = unique_colors

    # Threshold: < 2  (monochrome only — 2-color outline+fill is VALID SNES style)
    if unique_colors < 2:
        return True, "unique_colors<2", metrics

    # --- entropy ---
    if index_grid:
        cnt = Counter(idx for idx in index_grid if idx != transparent_i)
        entropy = compute_entropy({str(k): v for k, v in cnt.items()})
    else:
        entropy = 99.0
    metrics["entropy"] = round(entropy, 4)

    if entropy < 0.5:
        return True, "entropy<0.5", metrics

    # --- aspect ratio ---
    aspect = (width / height) if height > 0 else 999.0
    metrics["aspect_ratio"] = round(aspect, 4)

    if aspect > 4.0:
        return True, "aspect_ratio>4.0", metrics
    if aspect < 0.25:
        return True, "aspect_ratio<0.25", metrics

    return False, "", metrics


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

def quarantine_files(
    json_path: Path,
    dest_dir: Path,
    pack_name: str,
    category: str,
    reason: str,
    dry_run: bool,
    qmanifest_fh,
) -> None:
    """Move .png + .json + _seq.json to dest_dir.
    Non-negotiable: copy → verify destination exists and has same size → delete source.
    Never deletes source without confirming destination.
    """
    png_path  = json_path.with_suffix(".png")
    seq_path  = json_path.parent / f"{json_path.stem}_seq.json"

    entry = {
        "sprite_json":       str(json_path.relative_to(PROJECT_ROOT)),
        "pack_name":         pack_name,
        "sheet_dir":         json_path.parent.name,
        "quarantine_category": category,
        "quarantine_dir":    str((QUARANTINE / dest_dir).relative_to(PROJECT_ROOT)),
        "quarantine_reason": reason,
        "quarantined_at":    datetime.datetime.utcnow().isoformat(),
    }

    if not dry_run:
        dest_sheet = QUARANTINE / dest_dir / pack_name / json_path.parent.name
        dest_sheet.mkdir(parents=True, exist_ok=True)
        for f in (png_path, json_path, seq_path):
            if not f.exists():
                continue
            dst = dest_sheet / f.name
            # Copy
            dst.write_bytes(f.read_bytes())
            # Verify destination before deleting source
            if dst.exists() and dst.stat().st_size == f.stat().st_size:
                f.unlink()
            else:
                # Destination verification failed — leave source intact, log error
                entry.setdefault("errors", []).append(
                    f"verify_failed:{f.name} src={f.stat().st_size} dst={dst.stat().st_size if dst.exists() else 'missing'}"
                )
        if qmanifest_fh:
            qmanifest_fh.write(json.dumps(entry) + "\n")
            qmanifest_fh.flush()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus",  default=str(PROJECT_ROOT / "data" / "corpus" / "train"))
    parser.add_argument("--dry-run", action="store_true",
                        help="Report only — no files moved or deleted")
    args = parser.parse_args()

    corpus_dir = Path(args.corpus)
    if not corpus_dir.exists():
        print(f"ERROR: corpus not found: {corpus_dir}", file=sys.stderr)
        sys.exit(1)

    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    if not args.dry_run:
        for _, subdir, *_ in QUARANTINE_CATEGORIES:
            (QUARANTINE / subdir).mkdir(parents=True, exist_ok=True)
        (QUARANTINE / "ui_elements").mkdir(parents=True, exist_ok=True)

    # --- collect sprite JSON files via os.walk (faster than rglob on NTFS) ---
    print("Scanning corpus...", flush=True)
    json_files: list[Path] = []
    for root, dirs, files in os.walk(corpus_dir):
        dirs.sort()
        for fname in sorted(files):
            if (fname.endswith(".json")
                    and not fname.endswith("_seq.json")
                    and fname not in ("manifest.json", "tileset_meta.json")):
                json_files.append(Path(root) / fname)

    total_sprites = len(json_files)
    print(f"Found {total_sprites:,} sprite metadata files", flush=True)

    # --- first pass: assign pack name + count sprites per pack ---
    print("Counting sprites per pack...", flush=True)
    pack_total:  Counter          = Counter()
    sprite_pack: dict[Path, str]  = {}
    for jp in json_files:
        try:
            pack_name = jp.relative_to(corpus_dir).parts[0]
        except (ValueError, IndexError):
            pack_name = jp.parent.name
        pack_total[pack_name] += 1
        sprite_pack[jp] = pack_name

    # --- classify quarantine packs ---
    # Rule: texture > monochrome > outline > ui (single-sprite) — first match wins
    pack_category: dict[str, str | None] = {}  # pack_name → category key or None
    for pack_name in pack_total:
        cat = None
        for key, subdir, fn, note in QUARANTINE_CATEGORIES:
            if fn(pack_name):
                cat = key
                break
        if cat is None and pack_total[pack_name] == 1:
            cat = "ui_elements"
        pack_category[pack_name] = cat

    # Count quarantine sprites per category
    q_counts: Counter = Counter()
    for pack_name, cat in pack_category.items():
        if cat:
            q_counts[cat] += pack_total[pack_name]

    eligible = total_sprites - sum(q_counts.values())

    print(f"  Quarantine — texture_packs   : {q_counts['texture_packs']:,} sprites")
    print(f"  Quarantine — monochrome_packs: {q_counts['monochrome_packs']:,} sprites")
    print(f"  Quarantine — outline_art     : {q_counts['outline_art']:,} sprites")
    print(f"  Quarantine — ui_elements     : {q_counts['ui_elements']:,} sprites")
    print(f"  Eligible for artifact check  : {eligible:,}", flush=True)

    # Build lookup: category → (subdir, note)
    cat_meta: dict[str, tuple[str, str]] = {
        key: (subdir, note) for key, subdir, _, note in QUARANTINE_CATEGORIES
    }
    cat_meta["ui_elements"] = ("ui_elements", UI_NOTE)

    # --- second pass: quarantine or artifact-check each sprite ---
    log_fh       = None
    qmanifest_fh = None
    if not args.dry_run:
        log_fh       = open(LOG_PATH,  "w", encoding="utf-8")
        qmanifest_fh = open(QMANIFEST, "a", encoding="utf-8")

    artifacts:     list[dict] = []
    reason_counts: Counter    = Counter()
    pack_deleted:  Counter    = Counter()
    q_done:        Counter    = Counter()
    scanned = 0
    report_every = 10_000

    for json_path in json_files:
        pack_name = sprite_pack[json_path]
        scanned  += 1
        cat       = pack_category[pack_name]

        if cat:
            subdir, note = cat_meta[cat]
            quarantine_files(json_path, subdir, pack_name, cat, note,
                             args.dry_run, qmanifest_fh)
            q_done[cat] += 1
        else:
            # artifact check
            try:
                meta = json.loads(json_path.read_text(encoding="utf-8"))
            except Exception as exc:
                is_artifact, reason, metrics = True, f"unreadable_json:{exc}", {}
            else:
                is_artifact, reason, metrics = check_artifact(meta)

            if is_artifact:
                reason_counts[reason] += 1
                pack_deleted[pack_name] += 1
                png_path = json_path.with_suffix(".png")
                seq_path = json_path.parent / f"{json_path.stem}_seq.json"
                entry = {
                    "sprite_json":      str(json_path.relative_to(PROJECT_ROOT)),
                    "sheet_dir":        json_path.parent.name,
                    "pack_name":        pack_name,
                    "rejection_reason": reason,
                    "metrics":          metrics,
                    "deleted_at":       datetime.datetime.utcnow().isoformat(),
                }
                artifacts.append(entry)
                if not args.dry_run:
                    for p in (png_path, json_path, seq_path):
                        try:
                            p.unlink(missing_ok=True)
                        except OSError:
                            pass
                    if log_fh:
                        log_fh.write(json.dumps(entry) + "\n")
                        log_fh.flush()

        if scanned % report_every == 0:
            print(f"  {scanned:,}/{total_sprites:,} processed — "
                  f"{len(artifacts):,} artifacts so far...", flush=True)

    if log_fh:       log_fh.close()
    if qmanifest_fh: qmanifest_fh.close()

    # --- report ---
    total_deleted = len(artifacts)
    deletion_rate = total_deleted / eligible if eligible else 0.0
    total_removed = total_deleted + sum(q_done.values())
    overall_rate  = total_removed / total_sprites if total_sprites else 0.0

    DRY_RUN_PROJECTION = 44_086   # from dry-run 3 — 5% deviation gate
    DEVIATION_GATE     = 0.05

    print("\n" + "=" * 60)
    print("CORPUS CLEANING REPORT — LIVE RUN")
    print("=" * 60)
    print(f"  Total sprites scanned         : {total_sprites:,}")
    print(f"  Quarantined (texture_packs)   : {q_done['texture_packs']:,}")
    print(f"  Quarantined (monochrome_packs): {q_done['monochrome_packs']:,}")
    print(f"  Quarantined (outline_art)     : {q_done['outline_art']:,}")
    print(f"  Quarantined (ui_elements)     : {q_done['ui_elements']:,}")
    print(f"  Eligible for artifact check   : {eligible:,}")
    print(f"  Artifacts deleted             : {total_deleted:,}  ({deletion_rate:.1%} of eligible)")
    print(f"  Remaining in corpus           : {eligible - total_deleted:,}")
    print(f"  Overall removed rate          : {overall_rate:.1%}")
    if args.dry_run:
        print("  *** DRY RUN — no files moved or deleted ***")

    # 5% deviation check
    if not args.dry_run and DRY_RUN_PROJECTION > 0:
        deviation = abs(total_deleted - DRY_RUN_PROJECTION) / DRY_RUN_PROJECTION
        if deviation > DEVIATION_GATE:
            print(f"\n⚠  DEVIATION ALERT: actual deletions ({total_deleted:,}) deviate "
                  f"{deviation:.1%} from dry-run projection ({DRY_RUN_PROJECTION:,}) — "
                  f"exceeds {DEVIATION_GATE:.0%} gate.")
            print("  Cleaning pass completed but deviation flagged for human review.")
        else:
            print(f"\n  ✅ Deviation check PASS: {total_deleted:,} actual vs "
                  f"{DRY_RUN_PROJECTION:,} projected ({deviation:.1%} deviation, "
                  f"gate {DEVIATION_GATE:.0%})")

    print("\nDeletion reasons (of eligible sprites):")
    for reason, count in reason_counts.most_common():
        pct = count / eligible if eligible else 0
        print(f"  {reason:<35}  {count:>8,}  ({pct:.1%})")

    # flagged packs
    quarantine_set = {p for p, c in pack_category.items() if c}
    flagged = {
        p: (pack_deleted[p], pack_total[p], pack_deleted[p] / pack_total[p])
        for p in pack_total
        if p not in quarantine_set
        and pack_total[p] > 0
        and pack_deleted.get(p, 0) / pack_total[p] > FLAG_RATE
    }
    if flagged:
        print(f"\n⚠  FLAGGED PACKS (deletion rate >{FLAG_RATE:.0%}, excl. quarantine):")
        for pack, (deleted, total, rate) in sorted(flagged.items(), key=lambda x: -x[1][2]):
            print(f"  {pack:<60}  {deleted:>6,}/{total:<6,}  ({rate:.1%})")
    else:
        print(f"\n  No packs flagged above {FLAG_RATE:.0%} (excl. quarantine categories)")

    print(f"\nDeletion log : {LOG_PATH}" if not args.dry_run else "")
    print(f"Quarantine   : {QUARANTINE}" if not args.dry_run else "")
    print("=" * 60)


if __name__ == "__main__":
    main()
