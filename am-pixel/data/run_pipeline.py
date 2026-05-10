"""
run_pipeline.py — Full AM Pixel extraction + indexing pipeline orchestrator.

Stages:
  1. extractor.py  — slice sprite sheets into individual sprites
  2. indexer.py    — convert PNGs to palette-index JSON
  3. pixel_classifier.py — classify pixels into structural categories
  4. sequence_reorderer.py — reorder tokens into structure-aware sequence

Run from: /mnt/c/users/am-claw01/projects/absentmind-studio/am-pixel/data/
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
RAW_DIR      = SCRIPT_DIR / "raw"
PIPELINE_DIR = SCRIPT_DIR / "pipeline"
TRAIN_DIR    = SCRIPT_DIR / "corpus" / "train"
STATS_PATH   = SCRIPT_DIR / "corpus_stats.md"

MIN_SPRITE = 8
MAX_SPRITE = 256

sys.path.insert(0, str(PIPELINE_DIR))

# Import pipeline modules directly
import extractor          as ext_mod
import indexer            as idx_mod
import pixel_classifier   as cls_mod
import sequence_reorderer as seq_mod
import view_pair_detector as vpd_mod

from PIL import Image


# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_stem(path: Path) -> str:
    """Turn a path into a filesystem-safe flat stem for use as a dir name."""
    parts = path.relative_to(RAW_DIR).with_suffix("").parts
    return "__".join(p.replace(" ", "_").replace("/", "_") for p in parts)


def is_sheet_candidate(img: Image.Image) -> bool:
    """True if image looks like a sprite sheet (large + grid-friendly dims)."""
    w, h = img.size
    if w <= 32 or h <= 32:
        return False
    # At least one dimension is a clean multiple of 16 or 32
    w_ok = (w % 16 == 0) or (w % 32 == 0)
    h_ok = (h % 16 == 0) or (h % 32 == 0)
    return w_ok and h_ok


def pick_tile_size(img: Image.Image) -> tuple[int, int]:
    """Heuristically choose between 16x16 and 32x32 for grid extraction."""
    w, h = img.size
    # Prefer 32x32 if the image is large (≥ 128 in both dims) AND
    # dimensions are clean multiples of 32
    if w >= 128 and h >= 128 and (w % 32 == 0) and (h % 32 == 0):
        # Count how many 32x32 tiles vs 16x16 — pick the one that yields more
        # non-trivial cells (rough heuristic: just pick 32 for large sheets)
        return 32, 32
    return 16, 16


# ── Stage helpers ─────────────────────────────────────────────────────────────

def run_extractor(sheet_png: Path, out_dir: Path, tile_w: int, tile_h: int) -> list[dict]:
    """Call extractor.extract_sheet; return manifest."""
    try:
        manifest = ext_mod.extract_sheet(
            sheet_path=str(sheet_png),
            output_dir=str(out_dir),
            mode="grid",
            tile_w=tile_w,
            tile_h=tile_h,
            min_size=MIN_SPRITE,
        )
        return manifest
    except Exception as exc:
        print(f"  [extractor] ERROR on {sheet_png.name}: {exc}", file=sys.stderr)
        return []


def run_indexer(sprite_png: Path, sprite_json: Path) -> dict | None:
    """Call indexer.index_sprite; return result dict or None on error."""
    try:
        return idx_mod.index_sprite(str(sprite_png), str(sprite_json))
    except Exception as exc:
        print(f"  [indexer] ERROR on {sprite_png.name}: {exc}", file=sys.stderr)
        return None


def run_classifier(sprite_json: Path, cat_json: Path) -> dict | None:
    """Run pixel_classifier on indexed sprite JSON; return data dict or None."""
    try:
        with open(sprite_json, encoding="utf-8") as fh:
            sprite = json.load(fh)
        w: int = sprite["width"]
        h: int = sprite["height"]
        flat: list[int] = sprite["index_grid"]
        index_grid = [flat[row * w: row * w + w] for row in range(h)]

        cat_grid = cls_mod.classify_sprite(index_grid, w, h, five_category=False)
        dist = cls_mod.get_distribution(cat_grid)
        flat_cat = [c for row in cat_grid for c in row]
        output = {
            "sprite_id":     sprite.get("sprite_id", sprite_json.stem),
            "width":         w,
            "height":        h,
            "five_category": False,
            "category_grid": flat_cat,
            "distribution":  dist,
        }
        cat_json.parent.mkdir(parents=True, exist_ok=True)
        with open(cat_json, "w", encoding="utf-8") as fh:
            json.dump(output, fh, indent=2)
        return output
    except Exception as exc:
        print(f"  [classifier] ERROR on {sprite_json.name}: {exc}", file=sys.stderr)
        return None


def run_reorderer(sprite_json: Path, cat_json: Path, seq_json: Path) -> int:
    """Run sequence_reorderer; return token count or -1 on error."""
    try:
        seq = seq_mod.process_sprite_file(
            str(sprite_json), str(cat_json), str(seq_json)
        )
        return len(seq)
    except Exception as exc:
        print(f"  [reorderer] ERROR on {sprite_json.name}: {exc}", file=sys.stderr)
        return -1


# ── Dimension filter ──────────────────────────────────────────────────────────

def within_bounds(png: Path) -> tuple[bool, int, int]:
    """Return (ok, w, h); ok=False if outside [8..256] × [8..256]."""
    try:
        img = Image.open(png)
        w, h = img.size
        return (MIN_SPRITE <= w <= MAX_SPRITE and MIN_SPRITE <= h <= MAX_SPRITE), w, h
    except Exception:
        return False, 0, 0


def run_pair_detector(extracted: list[Path], out_dir: Path, source_sheet: str,
                      similarity_threshold: float = 0.6) -> int:
    """Run view_pair_detector on sprites from one sheet; write candidates.json.

    Builds a mini-manifest from the extracted PNGs, calls find_candidate_pairs,
    and writes <out_dir>/candidates.json.  Returns the number of pairs found,
    or -1 on error.  Skips silently if fewer than 2 sprites (no pairs possible).
    """
    if len(extracted) < 2:
        return 0

    mini_manifest: list[dict] = []
    for png in extracted:
        try:
            img = Image.open(png)
            w, h = img.size
        except Exception:
            continue
        mini_manifest.append({
            "sprite_id":    png.stem,
            "width":        w,
            "height":       h,
            "image_path":   str(png),
            "source_sheet": source_sheet,
        })

    if len(mini_manifest) < 2:
        return 0

    try:
        pairs = vpd_mod.find_candidate_pairs(mini_manifest, similarity_threshold)
        candidates_path = out_dir / "candidates.json"
        with open(candidates_path, "w", encoding="utf-8") as fh:
            json.dump({
                "source_sheet":          source_sheet,
                "sprite_count":          len(mini_manifest),
                "similarity_threshold":  similarity_threshold,
                "pair_count":            len(pairs),
                "candidates":            pairs,
            }, fh, indent=2)
        return len(pairs)
    except Exception as exc:
        print(f"  [pair_detector] ERROR on {source_sheet}: {exc}", file=sys.stderr)
        return -1




def main() -> None:
    TRAIN_DIR.mkdir(parents=True, exist_ok=True)

    all_pngs = sorted(RAW_DIR.rglob("*.png"))
    print(f"[pipeline] Found {len(all_pngs)} PNGs in {RAW_DIR}")

    # ── Counters ──────────────────────────────────────────────────────────────
    sheets_processed   = 0
    sheets_skipped     = 0
    sprites_extracted  = 0   # from sheet extraction
    sprites_direct     = 0   # individual sprites processed directly
    sprites_indexed    = 0
    sprites_classified = 0
    sprites_sequenced  = 0
    pairs_found        = 0   # view-pair candidates detected across all sheets
    errors: list[str]  = []
    dim_samples: list[tuple[int, int]] = []

    # ── Classify source PNGs ──────────────────────────────────────────────────
    sheet_pngs: list[Path] = []
    individual_pngs: list[Path] = []
    skipped_pngs: list[Path] = []

    for png in all_pngs:
        try:
            img = Image.open(png)
            w, h = img.size
            if is_sheet_candidate(img):
                sheet_pngs.append(png)
            elif MIN_SPRITE <= w <= MAX_SPRITE and MIN_SPRITE <= h <= MAX_SPRITE:
                individual_pngs.append(png)
            else:
                skipped_pngs.append(png)
        except Exception as exc:
            skipped_pngs.append(png)
            errors.append(f"open:{png.name}: {exc}")

    print(f"[pipeline] Sheet candidates:    {len(sheet_pngs)}")
    print(f"[pipeline] Individual sprites:  {len(individual_pngs)}")
    print(f"[pipeline] Skipped (non-sprite):{len(skipped_pngs)}")

    # ── STAGE 1: Extract sheets ───────────────────────────────────────────────
    print("\n[pipeline] === Stage 1: Sheet extraction ===")
    extracted_sprites: list[Path] = []   # PNGs produced by extractor

    for sheet_png in sheet_pngs:
        stem = safe_stem(sheet_png)
        out_dir = TRAIN_DIR / stem
        out_dir.mkdir(parents=True, exist_ok=True)

        img = Image.open(sheet_png)
        tw, th = pick_tile_size(img)

        print(f"  {sheet_png.name} ({img.width}×{img.height}) → tile {tw}×{th}")
        manifest = run_extractor(sheet_png, out_dir, tw, th)

        # If 16x16 yielded nothing, retry with 32x32
        if not manifest and tw == 16:
            print(f"    → 16x16 yielded nothing, retrying 32×32")
            manifest = run_extractor(sheet_png, out_dir, 32, 32)

        if manifest:
            sheets_processed += 1
            extracted = [Path(m["output_path"]) for m in manifest]
            extracted_sprites.extend(extracted)
            sprites_extracted += len(extracted)
            print(f"    → {len(extracted)} sprites")

            # Stage 1b: view-pair detection — run per-sheet immediately after extraction
            # so pair relationships are available before sequences are used for training.
            n_pairs = run_pair_detector(extracted, out_dir, source_sheet=sheet_png.stem)
            if n_pairs > 0:
                pairs_found += n_pairs
                print(f"    → {n_pairs} view-pair candidates (candidates.json)")
            elif n_pairs < 0:
                errors.append(f"pair_detector:{sheet_png.name}")
        else:
            sheets_skipped += 1
            errors.append(f"extract_empty:{sheet_png.name}")

    print(f"\n[pipeline] Sheets processed: {sheets_processed}  |  Extracted sprites: {sprites_extracted}")

    # ── Collect all sprites to process through stages 2-4 ────────────────────
    # Extracted sprites (from sheets) + individual source PNGs
    to_process: list[tuple[Path, Path]] = []   # (png_path, base_dir_for_jsons)

    for png in extracted_sprites:
        ok, w, h = within_bounds(png)
        if ok:
            dim_samples.append((w, h))
            to_process.append((png, png.parent))
        else:
            if w > 0:
                errors.append(f"size_skip:{png.name} ({w}×{h})")

    # Individual PNGs: place JSONs alongside PNG in a per-source-dir subdir
    for png in individual_pngs:
        stem = safe_stem(png)
        dest_dir = TRAIN_DIR / stem
        dest_dir.mkdir(parents=True, exist_ok=True)
        # Copy/link or just work in place — use png's own location for PNG,
        # but write JSON outputs into dest_dir
        dim_samples.append((0, 0))  # placeholder updated below
        ok, w, h = within_bounds(png)
        if ok:
            dim_samples[-1] = (w, h)
            to_process.append((png, dest_dir))
            sprites_direct += 1
        else:
            dim_samples.pop()
            errors.append(f"size_skip:{png.name}")

    print(f"[pipeline] Sprites to process (index/classify/reorder): {len(to_process)}")

    # ── STAGES 2-4 per sprite ─────────────────────────────────────────────────
    print("\n[pipeline] === Stages 2-4: Index → Classify → Reorder ===")

    for i, (png, base_dir) in enumerate(to_process, 1):
        stem = png.stem
        sprite_json = base_dir / f"{stem}.json"
        cat_json    = base_dir / f"{stem}_cat.json"
        seq_json    = base_dir / f"{stem}_seq.json"

        if i % 200 == 0:
            print(f"  [{i}/{len(to_process)}] ...")

        # Stage 2: index
        result = run_indexer(png, sprite_json)
        if result is None:
            errors.append(f"indexer:{png.name}")
            continue
        sprites_indexed += 1

        # Stage 3: classify
        cat = run_classifier(sprite_json, cat_json)
        if cat is None:
            errors.append(f"classifier:{png.name}")
            continue
        sprites_classified += 1

        # Stage 4: reorder
        n_tok = run_reorderer(sprite_json, cat_json, seq_json)
        if n_tok < 0:
            errors.append(f"reorderer:{png.name}")
            continue
        sprites_sequenced += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    # Filter out placeholder dims
    real_dims = [(w, h) for w, h in dim_samples if w > 0 and h > 0]
    dim_counter: dict[tuple[int, int], int] = {}
    for d in real_dims:
        dim_counter[d] = dim_counter.get(d, 0) + 1
    top_dims = sorted(dim_counter.items(), key=lambda x: -x[1])[:15]

    print("\n[pipeline] === Pipeline complete ===")
    print(f"  Source sheets processed:  {sheets_processed}")
    print(f"  Source sheets empty/skip: {sheets_skipped}")
    print(f"  Sprites from extraction:  {sprites_extracted}")
    print(f"  Individual sprites direct:{sprites_direct}")
    print(f"  Total sprites indexed:    {sprites_indexed}")
    print(f"  Total sprites classified: {sprites_classified}")
    print(f"  Total sprites sequenced:  {sprites_sequenced}")
    print(f"  View-pair candidates:     {pairs_found}")
    print(f"  Errors:                   {len(errors)}")

    # ── Write corpus_stats.md ─────────────────────────────────────────────────
    with open(STATS_PATH, "w", encoding="utf-8") as fh:
        fh.write("# AM Pixel Corpus Stats\n\n")
        fh.write("## Pipeline Run Summary\n\n")
        fh.write(f"- **Source PNGs scanned:** {len(all_pngs)}\n")
        fh.write(f"- **Sheet candidates processed:** {sheets_processed}\n")
        fh.write(f"- **Sheets skipped (empty/error):** {sheets_skipped}\n")
        fh.write(f"- **Sprites extracted from sheets:** {sprites_extracted}\n")
        fh.write(f"- **Individual sprites (direct):** {sprites_direct}\n")
        fh.write(f"- **Total sprites indexed:** {sprites_indexed}\n")
        fh.write(f"- **Total sprites classified:** {sprites_classified}\n")
        fh.write(f"- **Total sprites sequenced:** {sprites_sequenced}\n")
        fh.write(f"- **View-pair candidates found:** {pairs_found}\n")
        fh.write(f"- **Errors / warnings:** {len(errors)}\n\n")

        fh.write("## Top Sprite Dimensions (w×h : count)\n\n")
        for (w, h), cnt in top_dims:
            fh.write(f"- `{w}×{h}`: {cnt}\n")
        fh.write("\n")

        fh.write("## Error Log (first 50)\n\n")
        for e in errors[:50]:
            fh.write(f"- `{e}`\n")
        if len(errors) > 50:
            fh.write(f"- _... and {len(errors)-50} more_\n")
        fh.write("\n")

    print(f"\n[pipeline] Stats written → {STATS_PATH}")


if __name__ == "__main__":
    main()
