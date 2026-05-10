#!/usr/bin/env python3.14
"""
tools/run_triage_scorer.py
===========================
Scores entire Tier 2 corpus against the automated rubric (85-pt gate).
Resumable: skips sprites already in scores.json.
Outputs:
  data/golden_review/scores.json        — per-sprite scores + bucket
  data/golden_review/A_autopass/        — score >= 85 (copies, not moves)
  data/golden_review/B_borderline/      — score 70-84
  data/golden_review/C_autoreject/      — score < 70
  data/golden_review/D_anomaly/         — anomaly heuristics fired
  data/golden_review/E_tileset/         — tileset sprites (separate curation track)

Usage:
  python tools/run_triage_scorer.py [--corpus data/corpus/train] [--limit N] [--workers N]
"""
from __future__ import annotations
import argparse
import datetime
import json
import shutil
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT / "tools"))
sys.path.insert(0, str(PROJECT_ROOT / "data" / "pipeline"))

REVIEW_DIR = PROJECT_ROOT / "data" / "golden_review"
SCORES_PATH = REVIEW_DIR / "scores.json"

BUCKETS = {
    "A_autopass":  REVIEW_DIR / "A_autopass",
    "B_borderline": REVIEW_DIR / "B_borderline",
    "C_autoreject": REVIEW_DIR / "C_autoreject",
    "D_anomaly":   REVIEW_DIR / "D_anomaly",
    "E_tileset":   REVIEW_DIR / "E_tileset",
}

for d in BUCKETS.values():
    d.mkdir(parents=True, exist_ok=True)


def load_scores() -> dict:
    if SCORES_PATH.exists():
        try:
            return {e["sprite_id"]: e for e in json.loads(SCORES_PATH.read_text())}
        except Exception:
            return {}
    return {}


def save_scores(scores: dict) -> None:
    SCORES_PATH.write_text(json.dumps(list(scores.values()), indent=2))


def score_one(png: Path, sprite_json: Path | None) -> dict:
    from rubric_scorer import score_rubric_a

    # Detect if this is a tileset sprite by checking for tileset_meta.json sibling
    tileset_meta = png.parent / "tileset_meta.json"
    is_tileset = tileset_meta.exists()

    if is_tileset:
        result = {"total_auto": 0, "breakdown": {}, "issues": ["tileset — rubric A not applicable"], "rubric": "B"}
    else:
        try:
            result = score_rubric_a(
                str(png),
                str(sprite_json) if sprite_json and sprite_json.exists() else None,
            )
        except Exception as e:
            result = {"total_auto": 0, "breakdown": {}, "issues": [f"scorer_error: {e}"], "rubric": "A"}

    failure_modes = []
    if "pillow_shading" in str(result.get("issues", "")).lower() or any(
        "pillow" in i.lower() for i in result.get("issues", [])
    ):
        failure_modes.append("pillow_shading_detected")
    if any("banding" in i.lower() for i in result.get("issues", [])):
        failure_modes.append("banding_detected")
    if any("outline" in i.lower() or "black" in i.lower() for i in result.get("issues", [])):
        failure_modes.append("outline_issue")
    if any("sparse" in i.lower() for i in result.get("issues", [])):
        failure_modes.append("low_fill")
    if any("palette" in i.lower() and "color" in i.lower() for i in result.get("issues", [])):
        failure_modes.append("palette_bloat")

    score = result.get("total_auto", 0)
    if is_tileset:
        bucket = "E_tileset"
    elif score >= 85:
        bucket = "A_autopass"
    elif score >= 70:
        bucket = "B_borderline"
    else:
        bucket = "C_autoreject"

    bd = result.get("breakdown", {})
    return {
        "sprite_id":          png.stem,
        "source_path":        str(png),
        "sheet_dir":          str(png.resolve().parent.relative_to((PROJECT_ROOT / "data" / "corpus" / "train").resolve())),
        "total_score":        score,
        "subscores": {
            "A1_technical":    bd.get("technical_compliance", 0),
            "A2_construction": bd.get("construction_quality", 0),
            "A3_readability":  bd.get("readability", 0),
            "A4_animation":    bd.get("animation_quality", 0),
        },
        "primary_failure_modes": failure_modes,
        "rubric":             result.get("rubric", "A"),
        "is_tileset":         is_tileset,
        "bucket":             bucket,
        "scored_at":          datetime.datetime.utcnow().isoformat(),
    }


def apply_anomaly_detection(scores: dict) -> dict:
    """Post-pass: promote sprites to D_anomaly bucket using three heuristics."""
    all_scores = [e["total_score"] for e in scores.values() if not e["is_tileset"]]
    if not all_scores:
        return scores

    all_scores_sorted = sorted(all_scores, reverse=True)
    top5_threshold = all_scores_sorted[max(0, len(all_scores_sorted) // 20)]
    bottom10_threshold = all_scores_sorted[min(len(all_scores_sorted)-1, int(len(all_scores_sorted)*0.9))]

    # Heuristic 2: pack-level analysis — packs where >80% are A bucket
    pack_buckets: dict[str, list[str]] = defaultdict(list)
    for e in scores.values():
        pack_buckets[e["sheet_dir"]].append(e["bucket"])
    high_quality_packs = {
        pack for pack, buckets in pack_buckets.items()
        if buckets.count("A_autopass") / len(buckets) > 0.8
    }

    for sid, e in scores.items():
        if e["is_tileset"]:
            continue
        reasons = []

        # H1: high score but has failure mode flags
        if e["total_score"] >= top5_threshold and e["primary_failure_modes"]:
            reasons.append(f"H1: top-5% score ({e['total_score']}) with failure flags: {e['primary_failure_modes']}")

        # H2: low score in otherwise high-quality pack
        if e["total_score"] <= bottom10_threshold and e["sheet_dir"] in high_quality_packs:
            reasons.append(f"H2: bottom-10% outlier in high-quality pack ({e['sheet_dir']})")

        # H3: character sheet but extreme aspect ratio
        try:
            from PIL import Image
            with Image.open(e["source_path"]) as img:
                w, h = img.size
            ratio = max(w, h) / max(min(w, h), 1)
            sheet_cls = (e["sheet_dir"].split("/")[0] if "/" in e["sheet_dir"] else e["sheet_dir"])
            if ratio > 4.0 and not e["is_tileset"]:
                reasons.append(f"H3: extreme aspect ratio {w}x{h} (ratio {ratio:.1f}) for character sprite")
        except Exception:
            pass

        if reasons:
            scores[sid]["bucket"] = "D_anomaly"
            scores[sid]["anomaly_reasons"] = reasons

    return scores


def copy_to_bucket(entry: dict) -> None:
    src = Path(entry["source_path"])
    if not src.exists():
        return
    bucket_dir = BUCKETS[entry["bucket"]]
    # Preserve sheet context: bucket/sheet_dir/sprite.png
    dest = bucket_dir / entry["sheet_dir"] / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(src, dest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default=str(PROJECT_ROOT / "data" / "corpus" / "train"))
    parser.add_argument("--limit",   type=int, default=0, help="Max sprites to score (0=all)")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--skip-copy", action="store_true", help="Score only, skip bucket copies")
    args = parser.parse_args()

    corpus_dir = Path(args.corpus)
    all_pngs = sorted(corpus_dir.rglob("*.png"))
    print(f"Found {len(all_pngs):,} PNGs in {corpus_dir}")

    scores = load_scores()
    already_done = len(scores)
    print(f"Resuming: {already_done:,} already scored, {len(all_pngs)-already_done:,} remaining")

    to_score = [p for p in all_pngs if p.stem not in scores]
    if args.limit:
        to_score = to_score[: args.limit]
    print(f"Scoring {len(to_score):,} sprites with {args.workers} workers...")

    done = 0
    save_every = 500

    def score_task(png: Path) -> dict:
        sprite_json = png.parent / f"{png.stem}.json"
        return score_one(png, sprite_json)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(score_task, p): p for p in to_score}
        for fut in as_completed(futs):
            try:
                entry = fut.result()
                scores[entry["sprite_id"]] = entry
                done += 1
                if done % save_every == 0 or done == len(to_score):
                    save_scores(scores)
                    pct = (already_done + done) / len(all_pngs) * 100
                    print(f"  [{already_done+done:,}/{len(all_pngs):,}] {pct:.1f}% — saving...", flush=True)
            except Exception as e:
                print(f"  ERROR: {e}", file=sys.stderr)

    print("\nRunning anomaly detection...")
    scores = apply_anomaly_detection(scores)
    save_scores(scores)

    if not args.skip_copy:
        print("Copying sprites to review buckets...")
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            list(ex.map(copy_to_bucket, scores.values()))

    # Summary
    bucket_counts = defaultdict(int)
    for e in scores.values():
        bucket_counts[e["bucket"]] += 1

    print("\n=== TRIAGE COMPLETE ===")
    for b, cnt in sorted(bucket_counts.items()):
        print(f"  {b}: {cnt:,}")
    print(f"  TOTAL: {len(scores):,}")
    print(f"\nScores written to: {SCORES_PATH}")


if __name__ == "__main__":
    main()
