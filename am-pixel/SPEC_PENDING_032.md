# SPEC_PENDING — CHANGE-032: Tileset Edge Compatibility

**Status:** Pending — finalization deferred until Phase 4 empirical evaluation completes.

**Created:** 2026-05-10
**Decision reference:** `logs/decision_log.md` — Phase 3 | Architecture | D→C path adoption (2026-05-10)
**Resolved blocker:** `logs/BLOCKERS.md` — CHANGE-032 candidate (RESOLVED, 2026-05-10)
**Adoption path:** Option D (positional metadata, already implemented in Phase 3) → Option C (DNA-style tileset signatures, finalized post-Phase 4)

---

## Why This File Exists

The architectural decision to extend DNA-style locking to tilesets is committed. The exact format of tileset DNA — specifically, how much edge information must be carried in the signature — depends on what the foundation model learns implicitly from positional encoding during Phase 4 training.

If the model learns edge compatibility from positional metadata alone (`grid_x`/`grid_y` in `tileset_meta.json`), tileset DNA can carry a thin signature (corner palettes + outline weight). If it fails to learn implicitly, tileset DNA must incorporate explicit edge pixel tokens — the Option B mechanism, applied at the DNA level rather than globally.

Either way, the answer comes from running the model. This file holds the placeholder until that evidence exists.

---

## Phase 4 Trigger — Tileset Edge Compatibility Benchmark

The Phase 4 tileset edge compatibility benchmark (see `ROADMAP.md`, Phase 4 Tasks) produces an empirical binary signal:

| Result | Meaning | Tileset DNA format |
|--------|---------|-------------------|
| **PASS** (≥70% seam validation pass rate) | Model learned edge compatibility implicitly from positional encoding | Thin signatures — corner palettes + outline weight |
| **FAIL** (<70% seam validation pass rate) | Model did not learn implicitly | Full edge signatures — explicit edge pixel tokens per Option B mechanism, incorporated into DNA format |

This benchmark must complete before this file is finalized.

---

## What Will Be Specified Here Post-Phase 4

Once the benchmark result is known, this file will be replaced with a full spec amendment covering:

1. **Tileset DNA file format** — analogous to character DNA at `dna/characters/`; location will be `dna/tilesets/`
2. **Tileset approval gate procedure** — analogous to character DNA lock gate in `tools/compliance.py`; a human reviews and approves a tileset before its DNA is locked
3. **SPEC §9 amendment** — DNA locking section extended to cover tileset DNA alongside character DNA
4. **SPEC §10 amendment** — tileset generation section updated to specify conditioning on locked tileset DNA
5. **FOLDER_STRUCTURE.md addition** — `dna/tilesets/` directory added alongside `dna/characters/`
6. **Retrofit procedure** — how to reprocess `tileset_meta.json` files written during Phase 3 (grep for `edge_compatibility: "pending_spec_decision"` to identify all affected files)

---

## Current Phase 3 State

Tileset tiles are being written to corpus with:

```json
"edge_compatibility": "pending_spec_decision"
```

This flag is intentionally left unchanged until this file is finalized post-Phase 4. It is the single grep-able identifier for every tileset tile that needs reprocessing once the DNA format is locked.

The `tileset_id` and `grid_x`/`grid_y` fields written to `tileset_meta.json` are the Phase 3 positional metadata (Option D). These are committed and will survive regardless of which tileset DNA format is ultimately chosen — both thin and full-edge signatures will reference back to the same `tileset_id` and grid position records.

---

## Until This File Is Finalized

- Tileset tiles continue to be written to corpus with `edge_compatibility: "pending_spec_decision"`
- **Tileset generation training is blocked** at Phase 3 gate level for tileset asset types
- **Character training and generation are unaffected** — they proceed independently per existing spec
- The Phase 4 benchmark is the gate to finalizing this document
- Do not implement any tileset DNA format, `dna/tilesets/` directory, or SPEC §9/§10 amendments until this document is finalized

---

*AM Pixel SPEC_PENDING_032 — bound to SPEC.md, ROADMAP.md Phase 4, and logs/decision_log.md (CHANGE-032).*
