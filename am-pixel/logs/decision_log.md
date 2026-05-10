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
