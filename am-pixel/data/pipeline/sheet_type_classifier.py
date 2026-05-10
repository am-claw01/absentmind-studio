"""
data/pipeline/sheet_type_classifier.py
=======================================
Classifies extracted sprite sheets into three routing categories:

    CHARACTER  — character/animation sheets → eligible for view-pair detection
    TILESET    — environment/tileset sheets → tag with tileset_id + grid position,
                 skip pair detection
    AMBIGUOUS  — cannot determine with confidence → skip pairing, tag unclassified

The classification uses signals available from the extractor manifest alone —
no ML model, no additional I/O beyond what was already opened during extraction.

Signal definitions
------------------
Sprite count:
    Tilesets tend to have higher sprite counts per sheet (grid fills).
    Characters typically have lower counts (a handful of animation frames).

Dimension uniformity:
    Character sheets: all frames are identical size (animation frames).
    Tilesets: tiles are uniform by definition.
    → Both are uniform; not a discriminating signal by itself.

Palette variance across sprites:
    Character frames share most of their palette (same character, different pose).
    Tilesets share *some* palette but terrain tiles vary more (grass ≠ water ≠ rock).
    → Computed as mean pairwise palette-overlap across a random sample.

Source name heuristics:
    Folder/filename keywords strongly hint at sheet type.
    "character", "hero", "player", "enemy", "npc", "walk", "run", "idle", "attack"
      → CHARACTER bias
    "tile", "terrain", "map", "floor", "wall", "ground", "dungeon", "overworld"
      → TILESET bias

Thresholds (tunable):
    SPRITE_COUNT_TILESET_MIN  = 20   — sheets with ≥20 sprites lean tileset
    PALETTE_OVERLAP_HIGH      = 0.70 — mean overlap ≥0.70 → character-like
    PALETTE_OVERLAP_LOW       = 0.45 — mean overlap <0.45 → tileset-like
    SAMPLE_SIZE               = 12   — max sprite pairs sampled for palette check

Returns
-------
classify_sheet(manifest, sheet_path, extracted_pngs) -> SheetClassification
    dataclass with:
        sheet_type   : "character" | "tileset" | "ambiguous"
        confidence   : float in [0.0, 1.0]
        signals      : dict of computed signal values (for audit/debug)
        tileset_id   : str | None — set when sheet_type == "tileset"
"""

from __future__ import annotations

import itertools
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── Thresholds ─────────────────────────────────────────────────────────────
SPRITE_COUNT_TILESET_MIN = 20
PALETTE_OVERLAP_HIGH     = 0.70   # above → character
PALETTE_OVERLAP_LOW      = 0.45   # below → tileset
SAMPLE_SIZE              = 12     # pairs to sample for palette check

# ── Keyword lists ──────────────────────────────────────────────────────────
CHARACTER_KEYWORDS = {
    "character", "char", "hero", "player", "enemy", "npc", "monster",
    "walk", "run", "idle", "attack", "death", "hurt", "jump", "fall",
    "sprite_sheet", "anim", "animation", "warrior", "mage", "knight",
    "boss", "mob", "creature", "humanoid", "person", "figure",
}
TILESET_KEYWORDS = {
    "tile", "tileset", "tilemap", "terrain", "map", "floor", "wall",
    "ground", "dungeon", "overworld", "world", "environment", "env",
    "grass", "water", "stone", "rock", "sand", "dirt", "cave",
    "forest", "field", "road", "path", "indoor", "outdoor",
    "platform", "block", "brick", "wood", "metal", "ice", "lava",
}

SheetType = Literal["character", "tileset", "ambiguous"]


@dataclass
class SheetClassification:
    sheet_type:  SheetType
    confidence:  float
    signals:     dict = field(default_factory=dict)
    tileset_id:  str | None = None


# ── Helpers ─────────────────────────────────────────────────────────────────

def _name_keywords(sheet_path: Path) -> tuple[int, int]:
    """Return (character_hits, tileset_hits) from path tokens."""
    tokens = set(re.sub(r"[^a-z0-9]", " ",
                        sheet_path.stem.lower() + " " +
                        sheet_path.parent.name.lower()).split())
    char_hits = len(tokens & CHARACTER_KEYWORDS)
    tile_hits = len(tokens & TILESET_KEYWORDS)
    return char_hits, tile_hits


def _mean_palette_overlap(extracted_pngs: list[Path],
                           sample: int = SAMPLE_SIZE) -> float | None:
    """
    Compute mean pairwise palette-overlap (Jaccard) across a random sample
    of sprite pairs. Returns None if fewer than 2 valid sprites.

    Each sprite's palette is the frozenset of (R,G,B) tuples for opaque pixels.
    """
    if not HAS_PIL or len(extracted_pngs) < 2:
        return None

    def _palette(p: Path) -> frozenset:
        try:
            img = Image.open(p).convert("RGBA")
            colors: set = set()
            for r, g, b, a in img.getdata():
                if a >= 128:
                    colors.add((r, g, b))
            return frozenset(colors)
        except Exception:
            return frozenset()

    # Build palette cache for up to 2*sample sprites to avoid redundant I/O
    pool = extracted_pngs[:sample * 2]
    palettes = {p: _palette(p) for p in pool}
    # Drop empties
    palettes = {p: c for p, c in palettes.items() if c}
    if len(palettes) < 2:
        return None

    pairs = list(itertools.combinations(list(palettes.keys()), 2))
    if len(pairs) > sample:
        random.seed(42)
        pairs = random.sample(pairs, sample)

    overlaps = []
    for a, b in pairs:
        union = palettes[a] | palettes[b]
        if not union:
            continue
        overlaps.append(len(palettes[a] & palettes[b]) / len(union))

    return sum(overlaps) / len(overlaps) if overlaps else None


def _make_tileset_id(sheet_path: Path) -> str:
    """Generate a stable tileset_id from the sheet path stem."""
    return re.sub(r"[^a-z0-9_]", "_", sheet_path.stem.lower())[:64]


# ── Main classifier ─────────────────────────────────────────────────────────

def classify_sheet(
    manifest: list[dict],
    sheet_path: Path,
    extracted_pngs: list[Path],
) -> SheetClassification:
    """
    Classify a sheet as character, tileset, or ambiguous.

    Parameters
    ----------
    manifest:
        Extractor manifest list (each entry has sprite_id, width, height, etc.).
    sheet_path:
        Path to the source sheet PNG (used for name-keyword heuristics).
    extracted_pngs:
        Paths to extracted sprite PNGs (used for palette-overlap sampling).

    Returns
    -------
    SheetClassification
    """
    sprite_count   = len(manifest)
    char_kw, tile_kw = _name_keywords(sheet_path)
    mean_overlap   = _mean_palette_overlap(extracted_pngs)

    signals = {
        "sprite_count":        sprite_count,
        "char_keyword_hits":   char_kw,
        "tile_keyword_hits":   tile_kw,
        "mean_palette_overlap": round(mean_overlap, 4) if mean_overlap is not None else None,
    }

    # ── Scoring: +1 character evidence, -1 tileset evidence ──────────────
    score = 0.0       # positive → character, negative → tileset
    weight_total = 0.0

    # Keyword signal (weight 2)
    if char_kw > tile_kw:
        score += 2.0 * (char_kw / max(char_kw + tile_kw, 1))
    elif tile_kw > char_kw:
        score -= 2.0 * (tile_kw / max(char_kw + tile_kw, 1))
    weight_total += 2.0 if (char_kw + tile_kw) > 0 else 0.0

    # Sprite count signal (weight 1.5)
    if sprite_count >= SPRITE_COUNT_TILESET_MIN:
        score -= 1.5
    else:
        score += 0.5   # weak positive signal — small sheets slightly more likely char
    weight_total += 1.5

    # Palette overlap signal (weight 2.5 — strongest)
    if mean_overlap is not None:
        weight_total += 2.5
        if mean_overlap >= PALETTE_OVERLAP_HIGH:
            score += 2.5
        elif mean_overlap <= PALETTE_OVERLAP_LOW:
            score -= 2.5
        else:
            # Linear interpolation between LOW and HIGH
            t = (mean_overlap - PALETTE_OVERLAP_LOW) / (PALETTE_OVERLAP_HIGH - PALETTE_OVERLAP_LOW)
            score += 2.5 * (2 * t - 1)   # maps [0,1] → [-2.5, +2.5]

    signals["raw_score"] = round(score, 4)
    signals["weight_total"] = round(weight_total, 4)

    # ── Decision ──────────────────────────────────────────────────────────
    if weight_total == 0:
        # No signals available — can't classify
        return SheetClassification(
            sheet_type="ambiguous",
            confidence=0.0,
            signals=signals,
        )

    # Normalise to [-1, +1]
    normalised = score / weight_total
    signals["normalised_score"] = round(normalised, 4)

    CONFIDENCE_THRESHOLD = 0.30   # must be this far from 0 to commit

    if normalised >= CONFIDENCE_THRESHOLD:
        confidence = min(normalised / 1.0, 1.0)
        return SheetClassification(
            sheet_type="character",
            confidence=round(confidence, 4),
            signals=signals,
        )
    elif normalised <= -CONFIDENCE_THRESHOLD:
        confidence = min(abs(normalised) / 1.0, 1.0)
        tileset_id = _make_tileset_id(sheet_path)
        return SheetClassification(
            sheet_type="tileset",
            confidence=round(confidence, 4),
            signals=signals,
            tileset_id=tileset_id,
        )
    else:
        # Score too close to zero — ambiguous
        confidence = 1.0 - abs(normalised) / CONFIDENCE_THRESHOLD
        return SheetClassification(
            sheet_type="ambiguous",
            confidence=round(confidence, 4),
            signals=signals,
        )
