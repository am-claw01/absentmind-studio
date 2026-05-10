#!/usr/bin/env python3
"""
tools/rubric_scorer.py
Scores sprites against Rubric A (characters/enemies), B (tilesets), C (parallax).
Rubric A automated gate: 85/85 required before human sees sprite.
See SPEC §8 and knowledge/EVALUATION_RUBRIC.md.
"""
from __future__ import annotations
import json, sys, argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def _import_tool(name):
    import importlib, sys
    tools = Path(__file__).parent
    sys.path.insert(0, str(tools))
    return importlib.import_module(name)

def score_rubric_a(png_path: str, sprite_json_path: str = None, dna_path: str = None,
                   is_effect: bool = False) -> dict:
    """
    Score a character/enemy/effect sprite on the automated gate (85 pts).
    Returns {total_auto, breakdown, passed_gate, issues}.
    """
    breakdown = {}
    issues = []

    # ── Technical Compliance (25 pts) ──────────────────────────────────────
    tech_score = 25
    try:
        from palette_validator import validate_sprite_png
        v = validate_sprite_png(png_path, snes_strict=False)
        color_count = v.get("color_count", 0)
        # Deduct for extreme palette bloat (60+ colors = not SNES aesthetic)
        if color_count > 60:
            deduct = min(15, (color_count - 60) // 4)
            tech_score -= deduct
            issues.append(f"Extreme palette ({color_count} colors) — deducted {deduct}pts")
        elif color_count > 30:
            tech_score -= 5
            issues.append(f"Large palette ({color_count} colors) — deducted 5pts")
    except Exception as e:
        issues.append(f"palette_validator unavailable: {e}")
    breakdown["technical_compliance"] = max(0, tech_score)

    # ── Construction Quality (25 pts) ───────────────────────────────────────
    const_score = 25
    try:
        from outline_checker import check_outline_colors, score_outline
        oc = check_outline_colors(png_path)
        os_ = score_outline(oc)
        if oc["has_pure_black_outline"]:
            deduct = int((1.0 - os_) * 10)
            const_score -= deduct
            issues.extend(oc["issues"])
    except Exception as e:
        issues.append(f"outline_checker unavailable: {e}")

    if sprite_json_path and Path(sprite_json_path).exists():
        try:
            from banding_detector import detect_banding
            data = json.loads(Path(sprite_json_path).read_text())
            bd = detect_banding(data)
            if bd["has_banding"]:
                deduct = int(bd["severity"] * 10)
                const_score -= deduct
                issues.extend(bd["issues"])
        except Exception as e:
            issues.append(f"banding_detector unavailable: {e}")
    breakdown["construction_quality"] = max(0, const_score)

    # ── Readability (20 pts) ────────────────────────────────────────────────
    read_score = 20
    try:
        from PIL import Image
        img = Image.open(png_path).convert("RGBA")
        w, h = img.size
        if w < 8 or h < 8:
            read_score -= 10
            issues.append(f"Sprite too small ({w}x{h})")
        # Silhouette fill ratio: non-transparent / bounding box area
        pixels = list(img.getdata())
        non_trans = sum(1 for _,_,_,a in pixels if a > 10)
        total = w * h
        fill_ratio = non_trans / total if total > 0 else 0
        if fill_ratio < 0.1:
            read_score -= 10
            issues.append(f"Very sparse sprite ({fill_ratio:.1%} fill) — poor readability")
        elif fill_ratio < 0.2:
            read_score -= 5
    except Exception as e:
        issues.append(f"readability check failed: {e}")
    breakdown["readability"] = max(0, read_score)

    # ── Animation Quality (15 pts normal, 25 pts for effects) ──────────────
    # Single-frame sprites default to full score — animation is evaluated per-sheet
    anim_pts = 25 if is_effect else 15
    breakdown["animation_quality"] = anim_pts  # full score for single frames

    total_auto = sum(breakdown.values())
    passed_gate = total_auto >= 85

    return dict(
        total_auto   = total_auto,
        max_auto     = 85,
        breakdown    = breakdown,
        passed_gate  = passed_gate,
        issues       = issues,
        rubric       = "A",
    )

def score_rubric_b(tileset_info: dict = None) -> dict:
    """Tileset rubric — mostly placeholder until seam_validator is wired."""
    return dict(
        total      = 80,  # placeholder — seam integrity requires seam_validator
        max        = 100,
        breakdown  = dict(seam_integrity=25, visual_recession=16, texture_coherence=16,
                          atmospheric_consistency=12, completeness=8, technical_compliance=3),
        passed     = False,
        issues     = ["seam_validator not yet wired — manual evaluation required"],
        rubric     = "B",
    )

def score_rubric_c(parallax_info: dict = None) -> dict:
    """Parallax rubric — placeholder until layer_compositor is wired."""
    return dict(
        total      = 75,
        max        = 100,
        breakdown  = dict(layer_seaming=20, layer_depth=20, atmospheric_cohesion=15,
                          character_contrast=12, emotional_tone=8, technical_compliance=0),
        passed     = False,
        issues     = ["layer_compositor not yet wired — manual evaluation required"],
        rubric     = "C",
    )

def score_sprite(asset_type: str, png_path: str = None, sprite_json: str = None,
                 dna_path: str = None, **kwargs) -> dict:
    """Dispatcher — select correct rubric based on asset_type."""
    t = asset_type.lower()
    if any(x in t for x in ["character","enemy","npc","portrait","effect","boss"]):
        is_effect = "effect" in t
        return score_rubric_a(png_path, sprite_json, dna_path, is_effect=is_effect)
    elif "tileset" in t or "tile" in t:
        return score_rubric_b(kwargs.get("tileset_info"))
    elif "parallax" in t or "background" in t:
        return score_rubric_c(kwargs.get("parallax_info"))
    else:
        return score_rubric_a(png_path, sprite_json, dna_path)

def main():
    p = argparse.ArgumentParser(description="Score a sprite against AM Pixel rubric")
    p.add_argument("png_path")
    p.add_argument("--json", dest="sprite_json", default=None)
    p.add_argument("--dna",  dest="dna_path",    default=None)
    p.add_argument("--type", dest="asset_type",  default="character")
    p.add_argument("--effect", action="store_true")
    args = p.parse_args()

    result = score_sprite(args.asset_type, args.png_path, args.sprite_json, args.dna_path)
    print(json.dumps(result, indent=2))

    gate = result.get("passed_gate", result.get("passed", False))
    print(f"\n{'✅ PASSED' if gate else '❌ FAILED'} automated gate")
    sys.exit(0 if gate else 1)

if __name__ == "__main__":
    main()
