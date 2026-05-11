# decision_log.md

Reasoning log for **non-mechanical** decisions (CHANGE-027). Primary instrument for human and LLM drift detection.

**Mechanical trigger — an entry IS required when:**
- Choosing between two or more valid paths
- Governing instruction uses: if / may / consider / evaluate / when needed
- Deviating from a documented procedure, even slightly
- Deciding something is or is not a blocker
- Deciding a failure pattern warrants a specific intervention
- Any action with Risk Level **High** or **Irreversible**

**Mechanical execution** (running a script, commit after approval, installing a dependency, generating from a confirmed prompt) — **no** entry if fully specified by documents.

---

## Entry schema

```
## [ISO 8601 Date] | Phase [N] | [Category]

**Decision:** [One sentence]
**Governing Rule:** [Exact reference — e.g. SPEC §4.3 / CONSTITUTION Rule 5 / ROADMAP Phase 4 Gate]
**Alternatives Considered:** [What else and why rejected]
**Rationale:** [Why this choice]
**Confidence:** [Low / Medium / High]
**Risk Level:** [Low / Medium / High / Irreversible]
**Reversible:** [Yes / No — if No, recovery path]
```

**Categories:** Architecture | Quality | DataPipeline | PhaseGate | EscalationJudgment | ProcessDeviation

---

## 2026-05-09 | Phase 0 | ProcessDeviation

**Decision:** Use Python 3.14 system interpreter (not a project venv) for Phase 0 tool execution in WSL.
**Governing Rule:** ROADMAP Phase 0 — install dependencies, verify PyTorch functional
**Alternatives Considered:** (A) Create a dedicated virtualenv — preferred long-term but requires pip in venv first. (B) Use Hermes venv — stripped, no pip. (C) Use system Python 3.14 with --break-system-packages — fastest path to functional environment.
**Rationale:** WSL environment has no pip installed in any existing venv; system Python 3.14 is the only available interpreter with pip access via get-pip.py bootstrap. This is a dev-environment bootstrapping decision, not an architecture decision. A proper venv should be established before Phase 3 data pipeline work begins.
**Confidence:** High
**Risk Level:** Low
**Reversible:** Yes — venv can be created at any time; requirements.txt captures all dependencies.

---

*Initialized Phase 0 — CHANGE-027.*

## 2026-05-10 | Phase 3 | Architecture

**Decision:** Remove strict SNES 15-bit RGB (channels div-by-8) and hard 15-color cap from core pipeline validators. Move to optional --snes-strict flag only.
**Governing Rule:** SPEC §10.1 — hardware constraints not enforced by default. §10.2 — compliance is a post-processing filter.
**Alternatives Considered:** (A) Keep strict — contradicts spec, limits training data. (B) Optional flag (chosen) — train on SNES aesthetic, apply filter on export/generation when toggled.
**Rationale:** User correctly identified contradiction. Aesthetic-first training then compliance filter is the correct architecture. Easier to add filter than untrain hardware strictness.
**Confidence:** High
**Risk Level:** Low
**Reversible:** Yes.

---

## 2026-05-10 | Phase 3 | ProcessDeviation

**Decision:** Mirror AGENT_SKILL.md into the repository as `am-pixel/AGENT_SKILL.md`, treating the repo copy as canonical source of truth and the Hermes copy as a mirror.
**Governing Rule:** OPENCLAW_PROMPT Rule 11 (session startup protocol); CHANGE-026 (session logging); general auditability principle
**Alternatives Considered:** (A) Keep skill only in Hermes `~/.hermes/skills/` — not under version control, lost on reinstall, not auditable. (B) Mirror to repo (chosen) — git history tracks every change, survives framework changes, Kyle can inspect and audit the exact rules governing OpenClaw behavior.
**Rationale:** The skill is the document that prevents drift. Putting it under version control means changes to agent behavior are traceable, reviewable, and recoverable. The repo copy is updated first; Hermes copy is synced after.
**Confidence:** High
**Risk Level:** Low
**Reversible:** Yes

---

## 2026-05-10 | Phase 3 | Architecture

**Decision:** Implement `/checkpoint` command — re-reads Constitution + phase_gates + BLOCKERS, outputs alignment confirmation to chat, and appends a timestamped entry to `logs/checkpoint_log.md`.
**Governing Rule:** CONSTITUTION Rules 1–9 (all); CHANGE-028 (structural enforcement); user-identified risk: mid-session drift in long sessions
**Alternatives Considered:** (A) Chat-only confirmation (no disk write) — not auditable, lost in scrollback. (B) Cron-based auto-checkpoint — autonomous, but no human trigger. (C) On-demand command with disk write (chosen) — human-controlled, auditable, append-only log.
**Rationale:** The disk append is the critical part. A checkpoint that only prints to chat provides no persistent record. Writing to `checkpoint_log.md` means the alignment history is as auditable as the decision log and session log. Kyle can run `/checkpoint` whenever a session runs long and get both immediate confirmation and a permanent record.
**Confidence:** High
**Risk Level:** Low
**Reversible:** Yes

---

## 2026-05-10 | Phase 3 | ProcessDeviation

**Decision:** Add session boundary rules to AGENT_SKILL.md and startup protocol: write fresh session_log.md entry on compaction events, phase transitions, architectural decisions, and human-raised flags — not only at session start.
**Governing Rule:** CHANGE-026 (session logging); CHANGE-028 (structural enforcement); CONSTITUTION Rule 9 (human override authority)
**Alternatives Considered:** (A) Session start only (prior behavior) — misses mid-session resets caused by compaction or major corrections. (B) Every tool call — too granular, noisy. (C) Defined trigger events (chosen) — compaction, phase transition, architectural change, human correction. Covers the cases where drift is most likely without creating log noise.
**Rationale:** Context compaction is the primary drift risk in long sessions. If compaction occurs and I don't re-anchor, I may resume with stale assumptions. The session boundary rule forces a re-read of Constitution + phase_gates + BLOCKERS at every major inflection point — not just at session open.
**Confidence:** High
**Risk Level:** Low
**Reversible:** Yes

---

## 2026-05-10 | Phase 3 | DataPipeline

**Decision:** Wire `view_pair_detector.find_candidate_pairs()` into `run_pipeline.py` as Stage 1b — called per-sheet immediately after extraction, before index/classify/reorder passes. Writes `candidates.json` alongside sequences in each sheet's output directory.
**Governing Rule:** SPEC §6 (view-pair training data); ROADMAP Phase 3 — corpus must include view-pair relationship metadata before training; Constitution Rule 5 — data structure decisions made before data enters pipeline, not retrofitted after
**Alternatives Considered:** (A) Retrofit after pipeline completes — runs on already-processed corpus but thousands of sheets already lack candidates.json by morning. (B) Separate post-process script — decoupled but requires a second pass over all corpus dirs. (C) Inline per-sheet Stage 1b (chosen) — runs on extracted PNGs before they enter stages 2–4, data is available immediately, zero retrofit cost for new sheets.
**Rationale:** Kyle identified the gap before corpus grew too large to retrofit cleanly. Per-sheet detection is O(n²) per sheet, not O(N²) over the full corpus — manageable at 20–80 sprites per sheet. candidates.json is written to each sheet's output dir alongside the sequences, consistent with the existing file layout. Pair count is tracked in counters and written to corpus_stats.md.
**Confidence:** High
**Risk Level:** Low
**Reversible:** Yes — candidates.json files can be regenerated or deleted without affecting sequences.

---

## 2026-05-10 | Phase 3 | DataPipeline

**Decision:** Add `sheet_type_classifier.py` as Stage 1b in the pipeline — classifies each sheet as `character`, `tileset`, or `ambiguous` before routing to pair detection or tileset tagging.
**Governing Rule:** SPEC §6 (view-pair training data); Constitution Rule 5 (data structure committed before training, not retrofitted); Rule 8 (accuracy first — false-positive pairs from tilesets degrade model quality)
**Alternatives Considered:** (A) Run pair detection on all sheets — produces false positives on tilesets (palette-similar tiles are not view pairs). (B) Skip pair detection entirely — loses character view-pair signal. (C) Sheet-type classify first, route accordingly (chosen) — character sheets get pair detection, tilesets get tileset_id + grid position tags, ambiguous sheets skip pairing rather than guess.
**Rationale:** Palette-overlap heuristic cannot distinguish "same character, different direction" from "same tileset, different terrain type" without additional signal. Classification uses three independent signals (name keywords, sprite count, mean palette overlap) with explicit confidence scoring. Ambiguous sheets default to safe path (no pairing) rather than guessing. Thresholds are tunable in the classifier.
**Confidence:** High
**Risk Level:** Low
**Reversible:** Yes — sheet classification output files can be regenerated. Classifier thresholds tunable without reprocessing sprites.

---

## 2026-05-10 | Phase 3 | DataPipeline

**Decision:** Wire `view_pair_detector` and `sheet_type_classifier` into `harvest_loop.py`'s `run_pipeline_on()` function — the live pipeline. The previously patched `run_pipeline.py` was a batch script, not the function the harvest loop calls.
**Governing Rule:** Constitution Rule 5 (provenance and structure metadata written during ingestion, not retrofitted); ROADMAP Phase 3
**Alternatives Considered:** (A) Retrofit pairs onto existing corpus after harvest completes — exponentially harder as corpus grows; impossible to do per-sheet without re-opening all sprites. (B) Wire into `run_pipeline.py` only (prior incomplete fix) — does not affect the live harvest loop. (C) Wire into both `harvest_loop.py` and `run_pipeline.py` (chosen) — both the live loop and manual batch runs now apply sheet-type routing and pair detection.
**Rationale:** Kyle identified the gap while the harvest loop was actively running. Every sheet processed from this commit onward will have correct routing. Existing corpus sheets processed before this change will not have candidates.json or tileset_meta.json — a known gap, documented, acceptable since the training data commitment (Phase 4) has not been made yet.
**Confidence:** High
**Risk Level:** Low
**Reversible:** Yes.

---

## 2026-05-10 | Phase 3 | Architecture

**Decision:** Adopt D→C path for tileset edge compatibility (CHANGE-032). Option D (positional metadata only, already active via `grid_x/grid_y` in `tileset_meta.json`) is the Phase 3 implementation. Option C (DNA-style tileset signatures) is the committed architectural destination, with exact format deferred until Phase 4 empirical evaluation.
**Governing Rule:** SPEC §9 (DNA locking), SPEC §10 (tileset generation), CHANGE-032 (proposed); Constitution Rule 8 (accuracy first — do not commit a supervision strategy before knowing what the model needs)
**Alternatives Considered:**
- Option A (positional encoding, implicit learning) — already active via grid_x/grid_y. Does not commit to a supervision format. Risk: no fallback without retraining if implicit learning fails.
- Option B (explicit edge token approach) — explicit and reliable supervision; requires SPEC §4 and §5 amendments before Phase 3 corpus finalized. Premature — commits training data format before knowing if explicit supervision is needed.
- Option C (DNA-style edge signatures) — architecturally consistent destination; cannot be specified without knowing what edge information the model actually needs. Specifying now would be guessing.
- Option D (hybrid: positional now, edge supervision deferred) — chosen as the path to C. Avoids committing Phase 3 training data to a supervision strategy before Phase 4 evidence. Grid position already written. If model learns edge compatibility implicitly → C carries thin signatures. If not → C incorporates Option B mechanism.
**Rationale:** Option C is the architecturally-consistent destination — the project uses DNA-style locking for character continuity and tilesets deserve the same treatment. Option D is the empirically-honest path to get there. Specifying tileset DNA before Phase 4 evaluation means guessing the required edge information format. The Phase 4 tileset edge compatibility benchmark (added to ROADMAP) produces the empirical signal that determines the exact specification of tileset DNA. Deferring the spec until that signal exists is the correct sequence.
**Confidence:** High
**Risk Level:** Low — corpus continues to be collected with `edge_compatibility: "pending_spec_decision"` flag; a single grep identifies every tile needing retrofit when `SPEC_PENDING_032.md` is finalized. Character training proceeds unaffected.
**Reversible:** Yes — `tileset_meta.json` files with `edge_compatibility: "pending_spec_decision"` can be retrofitted once spec is finalized.

---

## 2026-05-10 | Phase 3 | DataPipeline

**Decision:** Add Golden Dataset triage system to streamline human curation. Pre-scores Tier 2 corpus with automated rubric gate, buckets sprites into A/B/C/D/E review surfaces, and provides a Flask curation UI. All golden accepts remain human-explicit.
**Governing Rule:** Constitution Rule 5 (data provenance — every golden sprite needs human accept + manifest entry); Rule 9 (human override authority — triage is a review surface, not automated curator)
**Alternatives Considered:** (A) Raw sprite-by-sprite review of ~50,000 sprites — impractical. (B) Fully automated acceptance at rubric threshold — violates Rule 5 and Rule 9. (C) Triage pre-scoring + human review per bucket (chosen) — reduces review burden while preserving human accept requirement for every golden entry. Generates rubric calibration data as byproduct.
**Rationale:** 493,193 sprites in corpus — exhaustive sprite-by-sprite review is not feasible. Triage surfaces the most likely candidates (A bucket) at the top, flags anomalies (D bucket) for closer inspection, and keeps tilesets (E bucket) on a separate track pending SPEC_PENDING_032.md finalization. Rubric calibration report generated from disagreement patterns feeds back into EVALUATION_RUBRIC.md before Phase 4 training.
**Confidence:** High
**Risk Level:** Low — augments human curation, does not replace it. Curation log captures all decisions with rubric scores at decision time, making any future rubric recalibration auditable.
**Reversible:** Yes

---

## DataPipeline — corpus_cleaning_pass_added
**Date:** 2026-05-10
**Type:** DataPipeline
**Trigger:** Initial triage review revealed grid-slicing artifacts in data/corpus/train/ — solid fills, edge slivers, near-empty tiles produced by the sheet extractor cutting on uniform grid boundaries regardless of sprite content.

**Decision:** Add `tools/clean_corpus.py` corpus cleaning pass to run on data/corpus/train/ before scoring or training. Artifacts are identified by four heuristics applied to sprite metadata (no re-extraction, no raw file access):
1. `unique_colors < 3` — solid fill or near-blank
2. `entropy < 0.5` — near-zero pixel entropy calculated from palette distribution
3. `transparency_ratio > 0.80` — >80% transparent pixels (empty tile)
4. `aspect_ratio > 4.0 or < 0.25` — extreme edge sliver

Deletion is atomic per sprite: `.png`, `.json`, and `_seq.json` deleted together. Every deletion logged to `data/golden_review/corpus_cleaning_log.jsonl` with pack name, sheet dir, rejection reason, and metric values. Packs with >50% deletion rate flagged for human review before their remaining sprites enter the Golden Dataset.

**Forward action:** Pre-filter heuristics to be added to the extractor (`data/pipeline/sequence_reorderer.py` or `run_pipeline.py`) so future harvest runs do not accumulate artifacts. This is a post-Phase 3 housekeeping task — current priority is cleaning the existing corpus first.

**Governing Rule:** Constitution Rule 4 (quality gate — below-threshold data does not enter training); Rule 5 (provenance integrity — cleaning log is part of the data provenance chain); Rule 9 (user decision — cleaning pass approved explicitly before execution)
**Alternatives Considered:** (A) Let artifacts pass through to triage scorer — scorer would mis-bucket them (high transparency = low rubric score = C-bucket, correct outcome but wastes scorer time and pollutes triage signal). (B) Filter at training time — deferred cost, artifacts still in corpus and visible during curation UI review. (C) Clean corpus now before scoring (chosen) — cleanest provenance, scorer and curation UI only see valid sprites.
**Confidence:** High
**Risk Level:** Low — deletes only files matching strict artifact criteria; log provides complete audit trail; dry-run mode available for verification before commit.
**Reversible:** No (deletions are permanent) — log retained as permanent record.

---

## DataPipeline — texture_packs_quarantined
**Date:** 2026-05-10
**Type:** DataPipeline
**Trigger:** Corpus cleaning dry-run flagged `texture-*` packs at 85–90% deletion rate under artifact heuristics. Root cause: texture tiles have intentionally uniform color distributions — the entropy and unique_colors checks correctly identify them as non-sprite art, but deletion would permanently discard potentially useful assets.

**Decision:** Quarantine all `texture-*` packs to `data/quarantine/texture_packs/` rather than delete. All three files per sprite (.png, .json, _seq.json) moved together. Quarantine manifest entry: *"Texture tiles — uniform color distribution, not character sprites, potentially useful for future texture generation track."* Assets are physically isolated from training corpus, fully recoverable, and excluded from all current scoring and curation passes.

**Governing Rule:** Constitution Rule 5 (provenance integrity — quarantine is logged, not silently discarded); Rule 9 (user decision — quarantine approach approved explicitly)
**Rationale:** Texture tiles are not sprite art and must not enter character sprite training. However, they may be valuable for a future texture/tileable-surface generation track. Quarantine preserves optionality without contaminating the current training corpus.
**Reversible:** Yes — files physically moved to quarantine, recoverable by moving back.

---

## DataPipeline — ui_elements_quarantined
**Date:** 2026-05-10
**Type:** DataPipeline
**Trigger:** Corpus cleaning dry-run flagged 717 single-sprite packs (pack_total == 1) at 100% deletion rate. These are Kenney UI element sheets (buttons, icons, arrows, bar segments) sliced into individual sprites — valid pixel art but not character sprites.

**Decision:** Quarantine all single-sprite packs to `data/quarantine/ui_elements/` rather than delete. Quarantine manifest entry: *"Kenney UI elements — buttons, icons, arrows — not sprite art, potentially useful for future UI generation track."* Same quarantine discipline as provenance quarantine — physically isolated, not in training, fully recoverable.

**Governing Rule:** Constitution Rule 5 (provenance integrity); Rule 9 (user decision — quarantine approach approved explicitly)
**Rationale:** UI elements are not character sprites and must not enter character sprite training. They are well-crafted pixel art assets that may be useful for a UI/icon generation track. Quarantine preserves optionality.
**Also decided:** `unique_colors` artifact threshold lowered from `< 3` to `< 2`. Two-color sprites (outline + fill) are valid SNES-style art and must not be rejected. Only truly monochrome single-color sprites are artifacts.
**Reversible:** Yes — files physically moved to quarantine, recoverable.

---

## DataPipeline — monochrome_packs_quarantined
**Date:** 2026-05-10
**Type:** DataPipeline
**Trigger:** Dry-run 2 flagged Kenney 1-bit-pack variants, micro-roguelike monochrome tiles, and small character sprite packs (blackMan8, blondeWoman2, greyMan8, etc.) at 100% deletion rate. Root cause: `unique_colors < 2` cannot distinguish intentional monochrome art from slicing artifacts.

**Decision:** Quarantine all 1-bit/monochrome packs and small character sprite packs (detected by name pattern: `(black|blonde|brown1|brown2|grey|red)(man|woman)\d`) to `data/quarantine/monochrome_packs/`. Manifest note: *"Intentional 1-bit/monochrome art — valid pixel art style, preserved for potential monochrome generation track. Not deleted because unique_colors < 2 cannot distinguish intentional monochrome from slicing artifacts."*

**Governing Rule:** Constitution Rule 5 (provenance); Rule 9 (user decision)
**Rationale:** These are intentional art styles, not extraction failures. Deletion would permanently destroy valid pixel art. Quarantine preserves them for a potential monochrome/1-bit generation track.
**Reversible:** Yes.

---

## DataPipeline — outline_art_quarantined
**Date:** 2026-05-10
**Type:** DataPipeline
**Trigger:** Dry-run 2 flagged `round_outline`, `round_nodetails_outline`, `square_nodetails_outline` etc. at ~53–55% deletion rate. Outline-only sprites have few filled colors by design — `unique_colors < 2` and `entropy < 0.5` fire as false positives.

**Decision:** Quarantine all packs matching `_outline` suffix to `data/quarantine/outline_art/`. Manifest note: *"Outline-only sprites — intentional art style, valid for outline generation training. Not deleted because low color count reflects style, not artifact."*

**Governing Rule:** Constitution Rule 5 (provenance); Rule 9 (user decision)
**Rationale:** Outline sprites are a valid and useful art style. May be specifically useful for training outline-generation or linework stages of a future pipeline.
**Reversible:** Yes.

---

## DataPipeline — medievalTile_retained_in_eligible
**Date:** 2026-05-10
**Type:** DataPipeline
**Trigger:** `medievalTile_*` packs flagged at 52–54% deletion rate in dry-run 2.

**Decision:** Do NOT quarantine `medievalTile_*` packs. They remain in the eligible artifact-check pool. Tileset tiles with low color variance are expected; the sprites that pass the adjusted thresholds are legitimate training data. The ~52% that fail are genuine artifacts (solid fills, transparent tiles) correctly caught by the heuristics.

**Governing Rule:** Rule 9 (user decision — explicit instruction to keep these in eligible pool)
**Rationale:** A 52% deletion rate with the remaining 48% being valid tileset sprites is acceptable. The cleaner is working correctly on these packs.
**Reversible:** N/A — no quarantine action taken.

---

## Architecture — CHANGE-033 Format Integrity Detection
**Date:** 2026-05-10
**Type:** Architecture
**Trigger:** Corpus class distribution analysis revealed that format integrity is not tracked anywhere in the manifest schema. JPEG-contaminated PNGs can pass all existing checks (license, source, transparency, color count lower-bound, entropy) while being unusable for autoregressive training — lossy compression inflates unique color count and destroys clean palette boundaries. This is both a data quality gap and a provenance gap.

**Decision:** Add CHANGE-033 — format integrity detection pass added to corpus pipeline. Implemented as `tools/format_integrity.py` and integrated into `clean_corpus.py`. Detection heuristic: unique non-transparent color count vs. resolution-dependent upper bound (64 for ≤16×16, 128 for ≤64×64). Suspects quarantined to `data/quarantine/format_suspect/`, never deleted. Four `format_provenance` fields written into every sprite_XXXX.json: `file_format`, `native_format`, `color_count_at_ingestion`, `palette_indexed`. At-ingestion integration: run_pipeline.py and harvest_loop.py write these fields at extraction time going forward.

**Governing Rule:** Constitution Rule 5 (data provenance — format integrity is part of the provenance chain); Rule 4 (quality gate — JPEG-contaminated sprites must not enter training)
**Alternatives Considered:** (A) Delete format_suspect sprites — rejected, may contain valid complex sprites that exceed bound legitimately. (B) Ignore format integrity at this phase — rejected, JPEG contamination is a silent training corruption vector. (C) Quarantine with full audit trail (chosen) — conservative, recoverable, auditable.
**Approval gate:** Human spot-check of format_suspect quarantine sample before any flagged packs are treated as permanently excluded.
**Confidence:** High
**Risk Level:** Low — quarantine only, no deletions, full audit trail.
**Reversible:** Yes (quarantine).

---

## Architecture — CHANGE-034 Multi-Class Semantic Labeling
**Date:** 2026-05-10
**Type:** Architecture
**Trigger:** Corpus class distribution analysis confirmed: no per-sprite semantic class labels exist anywhere in the pipeline. The `is_tileset` binary flag covers one dimension; pack-level `genre_hint` covers 33% of sprites usefully (67% are "mixed"). The transformer cannot condition generation on class type without per-sprite labels. Large single-class corpus additions are unsafe without class conditioning because the model cannot distinguish class distribution at training time.

**Decision:** Add CHANGE-034 — multi-class semantic labeling. Implemented as `tools/class_labeler.py`. Taxonomy: character (humanoid/monster/creature/npc), tileset (terrain/structure/dungeon/interior/exterior), environment (tree/rock/plant/water/structure/prop), effect (particle/projectile/explosion/magic/weather), ui (button/icon/panel/cursor/hud), item (weapon/armor/consumable/key_item/treasure), vehicle (ground/air/water/space), unknown. Rule-based only — pack name and path keywords. `unknown` is always the no-confidence fallback; silent miscategorization is explicitly rejected as worse than acknowledged unknown. Writes `sprite_class` + `sprite_subclass` + `class_confidence` + `class_rule_matched` into every sprite_XXXX.json. `sheet_type_classifier.py` extended to output class taxonomy alongside existing binary classification. At-ingestion integration: run_pipeline.py and harvest_loop.py write class labels at extraction time going forward. Missing `sprite_class` field treated as format violation.

**Governing Rule:** Constitution Rule 4 (quality gate — class conditioning required for Phase 4 training); Rule 9 (user decision — class taxonomy and approval gates defined by user)
**Approval gates (mandatory before Phase 4):**
1. Unknown class rate < 15% — if higher, report which packs drive unknowns, propose rule additions, re-run after approval
2. Human spot-check of 20-sprite sample per class for labeling accuracy
3. Human spot-check of format_suspect quarantine for false positives
**Alternatives Considered:** (A) ML-based classifier — rejected for Phase 3, no labeled training data exists yet, rule-based is transparent and auditable. (B) Manual labeling — impractical at 79,758 sprites. (C) Rule-based with unknown fallback (chosen) — auditable, no silent miscategorization, refinable iteratively.
**Confidence:** High on approach; Medium on initial unknown rate (may exceed 15% on first pass, refinement protocol defined)
**Risk Level:** Medium — mislabeling possible, mitigated by confidence logging, spot-check gates, and patch-ability of labels without re-extraction.
**Reversible:** Yes — labels are fields in sprite_XXXX.json, correctable without re-extraction.

---
