# PROPOSED_CHANGES_004.md
**AM Pixel Bible — Proposed Changes Series 004**
**Absentmind Studio | Data Integrity & Class Labeling**

Items in this document are staged for review before acceptance into the Bible.
Format: CHANGE-NNN header, type, priority, problem, proposed resolution, risk.

---

## CHANGE-033 — Format Integrity Detection and Provenance

**Type:** DataPipeline / ManifestSchema
**Priority:** High — must complete before Phase 4 training
**Affected documents:** SPEC.md (§15), FOLDER_STRUCTURE.md, clean_corpus.py, run_pipeline.py, harvest_loop.py

### Problem

The provenance manifest currently tracks license and source but not format integrity. JPEG-contaminated sprites can pass all license and source checks while being unusable for autoregressive transformer training — their color spaces are corrupted by lossy compression, which inflates unique color counts, destroys clean palette edges, and introduces sub-pixel color noise that cannot be tokenized cleanly. A 16×16 sprite with 180 unique colors is almost certainly a JPEG-contaminated PNG, not a pixel art sprite, regardless of its declared source.

Format integrity is a legal data quality concern as well as a training quality concern: we must be able to demonstrate the provenance chain from source to tokenized training sequence, and that chain requires knowing whether a file was natively lossless or was converted from a lossy source.

### Proposed Resolution

**1. JPEG contamination detection in clean_corpus.py:**

For each sprite, after existing artifact checks, check unique non-transparent color count against a resolution-dependent upper bound:
- 16×16 or smaller: max 64 unique non-transparent colors
- 17×32 or 33×64: max 128 unique non-transparent colors
- Larger than 64×64: no upper bound check (larger sprites may legitimately have more colors)

Sprites exceeding the bound for their resolution are moved to `data/quarantine/format_suspect/` — never deleted. Manifest note: "Color count exceeds expected upper bound for resolution — suspected JPEG-contaminated PNG or misclassified photograph."

Source packs with >20% format_suspect rate are flagged for human review in the cleaning report.

**2. New `format_provenance` fields added to every sprite_XXXX.json:**

```json
{
  "format_provenance": {
    "file_format": "png",
    "native_format": "png_native" | "png_from_jpeg_suspected" | "unknown",
    "color_count_at_ingestion": 42,
    "palette_indexed": true | false
  }
}
```

- `file_format`: always "png" (non-PNG rejected at scrape time, this field documents the check happened)
- `native_format`: "png_from_jpeg_suspected" if color_count exceeds resolution bound; "png_native" if within bound; "unknown" if metadata unavailable
- `color_count_at_ingestion`: unique non-transparent color count at the time the sprite was processed — permanent record, never updated
- `palette_indexed`: true if the source PNG uses a palette-indexed color mode, false if RGBA/RGB

**3. Run format integrity pass against cleaned corpus (Step 2 of coordinated execution).**

**4. At-ingestion integration:** run_pipeline.py and harvest_loop.py write format_provenance fields at extraction time. From this point on, no sprite enters data/corpus/train/ without format_provenance fields. Missing fields are treated as format_unknown and flagged.

### Risk

Low. Detection is conservative — color count upper bound is generous (64 colors for a 16×16 sprite allows valid complex pixel art while catching obvious JPEG contamination). Quarantine, not deletion. No existing clean sprites are affected by the format_suspect upper bound at the resolutions of the current corpus. Full audit trail in corpus_cleaning_log.jsonl and quarantine_manifest.jsonl.

### Approval gate

Human spot-check of a sample from format_suspect quarantine before any sprites from flagged packs are removed from the eligible pool permanently.

---

## CHANGE-034 — Multi-Class Semantic Labeling

**Type:** Architecture / DataPipeline
**Priority:** High — blocks Phase 4 training (class conditioning required)
**Affected documents:** SPEC.md (§3.2, §15), sheet_type_classifier.py, run_pipeline.py, harvest_loop.py, data/corpus/train/ (all sprite_XXXX.json files)

### Problem

Class conditioning is required for high-quality generation at inference time and required for safe corpus expansion. Without per-sprite class labels, balance between classes is the only protection against model bias toward dominant classes — which caps how much the corpus can grow and prevents the model from conditioning generation on sprite type at inference time.

Current state: the corpus has no per-sprite semantic class labels. The `is_tileset` binary flag (present in 437 sheet dirs via tileset_meta.json) and the pack-level `genre_hint` field in TRAINING_PROVENANCE_MANIFEST.json (67% "mixed") are insufficient. There is no `character`, `effect`, `environment`, `weapon`, `item`, `vehicle`, or `ui` label at the sprite level.

### Proposed Resolution

**1. Class taxonomy (primary + subclass):**

| primary_class | subclasses |
|---|---|
| `character` | humanoid, monster, creature, npc |
| `tileset` | terrain, structure, dungeon, interior, exterior |
| `environment` | tree, rock, plant, water, structure, prop |
| `effect` | particle, projectile, explosion, magic, weather |
| `ui` | button, icon, panel, cursor, hud |
| `item` | weapon, armor, consumable, key_item, treasure |
| `vehicle` | ground, air, water, space |
| `unknown` | (no subclass when primary is unknown) |

`unknown` is a valid and required output — never guess. Silent miscategorization is worse than acknowledged unknown.

**2. tools/class_labeler.py — multi-class tagger:**

- Reads each sprite_XXXX.json in data/corpus/train/
- Applies keyword rule set derived from pack name + path structure
- Writes `sprite_class` (primary) and `sprite_subclass` (optional) into sprite_XXXX.json
- Logs confidence and matched rule for every sprite — auditable
- Reports: count per primary class, sub-distribution, unknown rate, which packs drove unknowns

Rule set derived from Kenney, LPC, and OpenGameArt naming conventions. Uses path structure (e.g. `characters/`, `tiles/`, `ui/`) where available, pack name keywords otherwise. No ML — pure rule matching, transparent and auditable.

**3. sheet_type_classifier.py extended** to output primary class + subclass alongside existing character/tileset/ambiguous classification.

**4. At-ingestion integration:** run_pipeline.py and harvest_loop.py write `sprite_class` + `sprite_subclass` at extraction time. `unknown` is acceptable; missing field is not.

**5. Approval gate:**

- Unknown class rate must be **below 15%** after initial run
- Human spot-check of 20-sprite samples per class before Phase 4 approval
- If unknown rate > 15%: report which packs are driving unknowns, propose rule additions, re-run after approval

### Risk

Medium. Mislabeling is possible from keyword rules alone — some packs have ambiguous names. Mitigated by: (a) `unknown` is always the fallback — no forced labeling; (b) confidence score logged per sprite enables filtering low-confidence labels before training; (c) spot-check gate with 20-sprite samples per class before Phase 4; (d) labels are written into sprite_XXXX.json and can be corrected in a patch pass without re-extraction.

---

*End of PROPOSED_CHANGES_004.md v0.1*
*CHANGE-033 and CHANGE-034 staged for coordinated corpus pass after cleaning completes.*

---

## CHANGE-033 AMENDMENT v0.2 — Per-Size Threshold Table

**Date:** 2026-05-11
**Amends:** CHANGE-033 § Detection heuristic

### Problem with v0.1

The v0.1 implementation used a fixed 64-color threshold for sprites ≤16×16 and 128-color threshold for ≤64×64, leaving 48×48, 96×96, and 128×128 sprites unchecked. These are valid SNES-era sizes (LPC 64×64 characters, Arkanos 128×128 bosses).

### Replacement: Per-Size Threshold Table

Threshold is keyed on `max(width, height)` rounded up to the nearest table entry:

| max(w,h) | max unique non-transparent colors |
|---|---|
| ≤16  | 64  |
| ≤32  | 128 |
| ≤48  | 192 |
| ≤64  | 256 |
| ≤96  | 384 |
| ≤128 | 512 |
| >128 | 512 (conservative cap — oversized sprites are unusual, cap stays) |

**Rationale:** pixel art color budget scales sublinearly with sprite area. Threshold ≈ `max(w,h) × 4` approximates "color budget grows with detail-bearing capacity" and matches empirical observation in clean pixel art at each resolution. Non-tabled sizes round up to nearest entry.

### Dry-run report addition

CHANGE-033 dry-run must include empirical color-count distribution per size class:
- count, mean, median, 95th percentile, 99th percentile, max unique colors
- Used to validate thresholds are not over-triggering before live execution

---

## CHANGE-034 AMENDMENT v0.2 — Full Sprite Metadata Schema

**Date:** 2026-05-11
**Amends:** CHANGE-034 — expands from sprite_class/subclass only to full permanent schema

### Rationale

The dataset schema is a permanent contract. Fields that exist on every sprite after CHANGE-034 become required fields for every future sprite. Full schema defined once now, rather than accumulated in later passes.

### Complete sprite_XXXX.json schema post CHANGE-033 + CHANGE-034

**Existing (from indexer):**
```
width, height, palette, index_grid, transparent_index
```

**CHANGE-033 fields (format provenance):**
```
file_format              : "png" — always
native_format            : "png_native" | "png_from_jpeg_suspected" | "unknown"
color_count_at_ingestion : int — permanent record
palette_indexed          : bool
```

**CHANGE-034 fields:**

| Field | Type | Vocabulary | Coverage target | Nullable |
|---|---|---|---|---|
| `sprite_class` | str | character\|tileset\|environment\|effect\|ui\|item\|vehicle\|unknown | ≥85% non-unknown | No |
| `sprite_subclass` | str\|null | extensible per class | best-effort | Yes |
| `class_confidence` | float | 0.0–1.0 | 100% | No |
| `class_rule_matched` | str | rule identifier | 100% | No |
| `aesthetic_style` | str | closed (see below) | ≥70% non-unknown | No |
| `aesthetic_subclass` | str\|null | extensible | best-effort | Yes |
| `animation_id` | str\|null | pack+sheet+sequence id | nullable | Yes |
| `frame_index` | int\|null | 0-indexed | null iff animation_id null | Yes |
| `frame_count` | int\|null | total frames | null iff animation_id null | Yes |
| `animation_type` | str\|null | walk\|idle\|attack\|cast\|death\|jump\|hurt\|other | null iff animation_id null | Yes |
| `pose_direction` | str\|null | north\|south\|east\|west\|NE\|NW\|SE\|SW | char sprites only | Yes |
| `view_angle` | str\|null | front\|back\|side_left\|side_right\|three_quarter\|top_down | char sprites only | Yes |
| `rubric_score` | int | 0–100 | 100% (from scores.json) | No |
| `rubric_bucket` | str | A\|B\|C\|D\|E | 100% (from scores.json) | No |
| `perceptual_hash` | str | 16-char hex (pHash) | 100% | No |

**aesthetic_style closed vocabulary:**
`snes_jrpg` | `snes_action` | `snes_platformer` | `nes_classic` | `gba_jrpg` | `modern_indie` | `modern_minimal` | `monochrome` | `retro_arcade` | `isometric` | `top_down` | `unknown`

### Extraction strategies

**aesthetic_style:** pack-level rule engine. Kenney medieval-rts → `snes_jrpg`. LPC base → `snes_jrpg`. Kenney 1-bit → `monochrome`. Kenney platformer → `snes_platformer`. Modern indie packs → `modern_indie`. Default: `unknown`.

**animation_id / frame_index / pose_direction / view_angle — LPC canonical layout:**
LPC character sheets use a 13×21 grid (7 frames × 4 directions per animation type). Row groups (each 4 rows = N/W/S/E):
- Rows 0–3: cast; 4–7: thrust; 8–11: walk; 12–15: slash; 16–19: shoot; row 20: hurt
- Derivable from `sheet_y / tile_height` (row index) → animation_type + pose_direction
- `frame_index` = `sheet_x / tile_width` within the row

**Kenney character packs:** per-pack rules for known layouts. Default null for unrecognized layouts.

**OGA character sheets:** layout varies. Default null unless specific pack rules defined.

**Non-character sprites:** animation/pose fields always null.

**perceptual_hash:** `imagehash.phash(Image.open(png_path))` → 16-char hex. Stored once at ingestion.

**rubric_score / rubric_bucket:** read from `data/golden_review/scores.json` keyed by sprite_id (format: `packdir/sprite_XXXX.png`). Score 0 and bucket C/D assigned if not present (indicates pre-scoring artifact).

### Coverage gates for CHANGE-034 live run

- `sprite_class` non-unknown ≥ 85% — FAIL stops run
- `aesthetic_style` non-unknown ≥ 70% — FAIL stops run
- `rubric_score` coverage = 100% — FAIL stops run
- `perceptual_hash` coverage = 100% — FAIL stops run

### Dry-run report outputs

- `data/golden_review/resolution_distribution.json` — count per (width, height) tuple
- `data/golden_review/class_distribution.json` — count per primary class + subclass
- 20-sprite samples per sprite_class
- 20-sprite samples per aesthetic_style (where count ≥ 20)
- 20-sprite samples from animation sequences (animation_id non-null)
- Coverage table for all fields

---

*PROPOSED_CHANGES_004.md v0.2 — amendments to CHANGE-033 and CHANGE-034*
*v0.1: initial CHANGE-033 and CHANGE-034 definitions*
*v0.2: per-size threshold table (CHANGE-033), full schema expansion (CHANGE-034)*
