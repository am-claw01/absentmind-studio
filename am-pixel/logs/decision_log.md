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
