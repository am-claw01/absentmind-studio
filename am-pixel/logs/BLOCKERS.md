# BLOCKERS.md
# Documented blockers awaiting human input.
# A blocker is any task that cannot be resolved after 48 hours of genuine attempts.
# Format: Date | Phase | Task | What Was Attempted | Options | Status

| Date | Phase | Task | Attempted | Options | Status |
|------|-------|------|-----------|---------|--------|

## 2026-05-10 | Phase 3 | OPEN

**Blocker:** Tileset edge compatibility — spec decision required (CHANGE-032 candidate)

**Summary:** The pipeline now routes tileset sheets through `sheet_type_classifier.py` and writes `tileset_meta.json` with `edge_compatibility: "pending_spec_decision"` for every tile. This is a placeholder. The fundamental architectural question is unresolved: **how does the model learn to generate new tiles that edge-match existing tiles in a project?**

This is distinct from detecting existing tile pairs. It is a generation-conditioning problem. When a user says "make a snow variant of this grass tileset," the model must:
1. Know what edges the existing grass tiles expose at their seams
2. Generate snow tiles whose edges are compatible with those seams
3. Maintain consistent palette derivation (snow palette derived from grass, not arbitrary)

`tools/seam_validator.py` exists as a post-generation validation tool, but validation after generation is not the same as training the model to generate compatible tiles. The training data needs to encode edge-compatibility as a learnable signal.

**Approaches identified for evaluation (do not implement without spec decision):**

**Option A — Positional encoding approach**
Include each tile's position within its tileset sheet as sequence metadata (grid_x, grid_y already written to `tileset_meta.json`). The model learns adjacency rules implicitly from how tilesets are laid out in training data. Low implementation cost; relies on the model inferring edge rules without explicit supervision. May require a large tileset corpus to converge. No spec changes required beyond confirming positional metadata is used during training.

**Option B — Explicit edge token approach**
Extract the edge pixel rows/columns of each tile (top, bottom, left, right) and include them as conditioning tokens when generating neighboring tiles. Requires a new pipeline tool (edge extractor) and a new token type in the sequence format. Supervision is explicit — the model is directly told what edges it must match. Significant spec change: SPEC §4 (token format) and SPEC §5 (sequence ordering) both need amendments.

**Option C — DNA-style edge signature approach (most architecturally consistent)**
Treat exposed tileset edges like character DNA. When a tileset is approved (human review), lock the edge pixel patterns and palette derivation rules as a "tileset DNA" record, analogous to character DNA. New tiles generated for that tileset condition on the locked edge signature. This is the most consistent approach because the project already uses DNA-style locking for character continuity — it extends the same pattern to tilesets. Requires: (1) a tileset DNA format spec, (2) a tileset approval gate analogous to the character approval gate, (3) spec amendments to SPEC §9 (DNA locking) and SPEC §10 (tileset generation).

**Option D — Hybrid: positional metadata now, edge tokens later**
Implement Option A immediately (positional metadata is already being written). Defer explicit edge supervision to Phase 5+ once the model architecture is finalized. This avoids a training-data commitment before the architecture is locked. Risk: if the model fails to learn edge compatibility implicitly, retrofitting edge supervision post-training is costly.

**Additional consideration:** The three approaches above are not mutually exclusive. Option C (DNA-style) could incorporate Option B (edge tokens) as the signature format. The decision boundary is really: implicit learning (A/D) vs. explicit supervision (B/C).

**Phase gate impact:** Phase 3 cannot fully close for tileset generation training without this decision. Character sheet corpus can be finalized independently. Tileset tiles are being written to corpus with `edge_compatibility: "pending_spec_decision"` — they will not be used for generation training until this blocker is resolved.

**Attempted:** No resolution attempted. This is a CHANGE-032 candidate requiring Kyle's decision and likely a SPEC amendment before any implementation.

**Options:** See four options above. Kyle's input required.

**Status:** RESOLVED — D→C path adopted, awaiting Phase 4 empirical evaluation

**Resolution (2026-05-10):** Kyle adopted the D→C path. Option D (positional metadata — `grid_x/grid_y` in `tileset_meta.json`) is the active Phase 3 implementation. Option C (DNA-style tileset signatures) is the committed architectural destination, with the exact format deferred until Phase 4 empirical evaluation. Tileset DNA format will be finalized in `am-pixel/SPEC_PENDING_032.md` after Phase 4 training results are available.

**Decision log reference:** `logs/decision_log.md` — Phase 3 | Architecture | D→C path entry (2026-05-10)
**Spec placeholder:** `am-pixel/SPEC_PENDING_032.md`
**Phase gate note:** Tileset generation training remains blocked pending `SPEC_PENDING_032.md` finalization. Character training is unaffected and proceeds independently. `edge_compatibility: "pending_spec_decision"` flag in `tileset_meta.json` files remains accurate — path adopted but format pending.

---
