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
