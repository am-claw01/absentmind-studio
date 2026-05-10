# AM Pixel — Evaluation Rubric
**Knowledge Base | Phase 1 Boot Training**

---

## Overview

This rubric defines the exact scoring structure used to evaluate all AM Pixel assets. There are three rubrics, each matched to an asset type. Every criterion below is non-negotiable — partial credit exists, but the thresholds and gates are fixed. Nothing proceeds to the next stage until the current gate is fully cleared.

**Rubric A** — Character / Enemy / Portrait / Effect Sprites
**Rubric B** — Tilesets
**Rubric C** — Parallax Battle Backgrounds

All rubrics share a **95/100 passing threshold** for an individual asset.
Batch quality is tracked separately via a **99/100 batch pass rate** (see the dedicated section at the bottom).

---

---

# RUBRIC A — Character / Enemy / Portrait / Effect Sprites

## Gate Structure

Rubric A operates as a **two-gate pipeline**. The automated gate runs first. If the sprite does not score **85/85** on the automated gate, it is **never shown to a human** — it goes directly to full rebuild. Only a perfect automated score unlocks the human gate.

```
Automated Gate: 85 pts  (must score 85/85 — any point loss = FULL REBUILD)
Human Gate:     15 pts  (unlocked only after perfect automated score)
─────────────────────────
Total possible: 100 pts
Passing threshold: 95/100
```

> **Battle Effects Variant:** Animation Quality weight increases from 15 → 25 pts.
> Construction Quality decreases from 25 → 15 pts. All other weights and gate rules remain identical.

---

## AUTOMATED GATE — 85 Points

### A1 — Technical Compliance · 25 pts

**Tools:** `palette_validator.py`, `anti_aliasing_detector.py`

#### What Is Being Measured
Whether the sprite strictly conforms to the project's defined color palette and pixel construction rules. This includes: palette membership of every pixel, total color count within the per-asset limit, correct use of transparency, and the absence of anti-aliased edges (sub-pixel blending, partial alpha, or any pixel that falls between two intentional values).

#### Scoring Scale
- **25/25 (Full):** Every pixel maps to an approved palette entry. Zero anti-aliased pixels detected. Alpha channel contains only fully opaque or fully transparent values. Color count at or under the asset-class limit.
- **13–24 (Partial):** Minor violations — one or two stray off-palette pixels, a small cluster of semi-transparent edge pixels, or color count slightly over limit. The asset is structurally sound but non-compliant in isolated spots.
- **0/25 (Zero):** Any of the following: more than a negligible number of off-palette pixels, systematic anti-aliasing (e.g., an entire outlined edge treated with blending), use of an entirely wrong sub-palette, or gradient fills anywhere in the sprite.

#### Common Failure Patterns
- Exporting from a raster editor that applies its own resampling during resize (bilinear/bicubic instead of nearest-neighbor), which introduces interpolated edge colors that are off-palette.
- Using the "soften" or "blur" tool on outlines to reduce harshness — this reads as anti-aliasing.
- Accidentally including a color from a reference image that was never added to the approved palette.
- Confusion between the character sub-palette and the background sub-palette — using a background tone on a character sprite.
- Alpha values of 128 or 192 used for "shadow" areas instead of a dedicated shadow palette color.

---

### A2 — Construction Quality · 25 pts

**Tools:** `banding_detector.py`, `outline_checker.py`, `dna_diff.py`

#### What Is Being Measured
The structural correctness of the sprite as a pixel art object. This covers three distinct sub-concerns:

- **Banding** (`banding_detector.py`): Whether shading colors are arranged in repeating parallel bands rather than following the form of the surface. Banding flattens volume and reads as lazy shading.
- **Outline Integrity** (`outline_checker.py`): Whether the sprite's outer contour is a clean, intentional single-pixel outline with no gaps, double-pixel flatness on curved sections, or unintentional breaks. Includes checking that interior detail lines follow the same pixel discipline.
- **DNA Similarity** (`dna_diff.py`): Whether this sprite is structurally distinct from existing sprites in the project's asset library. Detects clones, palette-swaps-passed-off-as-new-designs, and frame copies that were not intentionally reused.

#### Scoring Scale
- **25/25 (Full):** No banding detected across any shaded region. Outline is clean and closed with intentional weight variation. DNA diff registers the sprite as sufficiently novel (or, for intentional reuse, as an approved re-use).
- **13–24 (Partial):** Isolated banding in one region (e.g., only the character's leg), minor outline roughness in one section, or a DNA diff score that is elevated but explainable by shared design language rather than copy-paste.
- **0/25 (Zero):** Pervasive banding across the majority of the sprite, multiple outline breaks or systematically double-pixel outlines, or a DNA diff that flags the sprite as a near-duplicate of an existing asset without approved justification.

#### Common Failure Patterns
- Shading by simply darkening the entire row of pixels below a highlight — produces immediate banding.
- Using the line tool to draw outlines instead of manually placing pixels, which creates staircasing artifacts that the outline checker flags as roughness.
- Reusing an idle animation frame from another character and only changing the head — dna_diff will catch the body match even if the palette is different.
- Interior lines (clothing folds, weapon edges) placed with no regard for the pixel grid, creating stray single pixels that read as noise rather than detail.
- Forgetting to close the outline on transparent-background sprites — leaving one-pixel gaps that the outline checker reports as breaks.

---

### A3 — Readability · 20 pts

**Tools:** Silhouette contrast analysis (internal), pixel-level legibility scan (internal)

#### What Is Being Measured
Whether the sprite communicates its intended form and role at its native resolution without scaling. Two sub-concerns:

- **Silhouette Contrast:** The sprite's outer shape must be immediately readable as its asset type (humanoid character, quadruped enemy, weapon, UI element, etc.). The silhouette — the sprite viewed as a flat black shape against a neutral background — must convey the pose and role unambiguously.
- **Pixel-Level Legibility:** Individual details within the sprite must be distinct and intentional at 1× zoom. No detail should require zooming in to understand; no region should read as a muddy blur of similar colors.

#### Scoring Scale
- **20/20 (Full):** Silhouette is immediately readable as the correct asset type and pose. All interior detail regions are distinct and contribute to readability. The automated scan finds no regions where adjacent pixels are too similar in luminance to register as separate details.
- **10–19 (Partial):** Silhouette is generally correct but one pose element is ambiguous (e.g., a raised arm reads as part of the head), or one interior region is muddied by insufficient contrast between adjacent colors.
- **0/20 (Zero):** Silhouette is unreadable — the asset type is not identifiable from shape alone. Or: the majority of interior detail is lost due to low contrast, making the sprite read as a colored blob at native resolution.

#### Common Failure Patterns
- Characters posed with arms close to the body, making the silhouette read as a featureless rectangle.
- Using two palette colors that are nearly identical in luminance to shade adjacent regions — they merge visually.
- Over-detailing small sprites: cramming so much internal line work into a 16×16 or 32×32 asset that no single detail reads cleanly.
- Background-colored fill in concave areas of the silhouette (e.g., between legs) that blends with the canvas, breaking the outline reads.
- Ignoring the "squint test" — if the sprite reads poorly when viewed through squinted eyes, it will read poorly at a distance or at small scale.

---

### A4 — Animation Quality · 15 pts *(Battle Effects: 25 pts)*

**Tools:** `effect_timing_evaluator.py`, pose consistency analysis (internal)

#### What Is Being Measured
Whether the sprite's animation frames are mechanically sound and visually convincing. Two sub-concerns:

- **Effect Timing** (`effect_timing_evaluator.py`): For effects (explosions, spell casts, impacts), whether frame durations follow a believable timing curve — typically fast initial impact, sustained mid-phase, rapid decay. Flat timing (every frame the same duration) always fails.
- **Pose Consistency:** Whether character animation frames maintain consistent volume, anchor points, and proportions across the cycle. A character's head should not grow or shrink between frames; a walk cycle's foot contact points should stay grounded.

#### Scoring Scale
- **15/15 Full (or 25/25 for Battle Effects):** Timing curves are non-linear and intentional. All frames maintain consistent proportions and anchor points. The animation reads as physically plausible at native playback speed.
- **8–14 Partial (13–24 for Battle Effects):** Timing is mostly correct but one section is flat or one frame has a noticeable volume inconsistency. The animation reads correctly overall but has a mechanical hiccup.
- **0 Zero:** Flat timing across the entire effect (all frames equal duration), or animation frames that are internally inconsistent enough to break the motion read (e.g., a character's torso shifting several pixels between adjacent frames with no in-between).

#### Common Failure Patterns
- Copy-pasting the first and last frame of an idle animation and calling the hold frames identical — creates a robotic snap.
- Battle effects with exactly 4 frames of equal duration because that was the default timeline setting.
- Walk cycles where the character's center of mass bobs up on both the left and right step instead of following a consistent arc.
- Explosion effects that play in linear order without any ease-in on the initial flash — misses the physical weight of the impact.
- Forgetting to account for the loop point: the last frame of a looping animation should flow cleanly into the first, with no jump in form or position.

---

## HUMAN GATE — 15 Points

*The human gate is unlocked only after the automated gate scores 85/85.*
*Human reviewers use the criteria below. There are no automated tools for this gate.*

---

### A5 — Originality · 10 pts

#### What Is Being Measured
Whether the sprite demonstrates a genuinely distinctive visual concept that is not derivative of existing genre tropes, reference material, or other AM Pixel assets in a shallow way. Originality does not mean "weird for its own sake" — it means the sprite makes a design choice that is unexpected, memorable, and belongs specifically to this world.

#### How a Human Reviewer Should Score This

**9–10 pts:** The sprite immediately reads as something specific to AM Pixel. Its design makes a choice you haven't seen before in this genre — a silhouette decision, a color relationship, a detail that implies backstory. You could describe it in one sentence and that description would not apply to any other sprite in the library.

**6–8 pts:** The sprite is competent and has a discernible identity, but its core design language borrows heavily from a familiar archetype (the standard dark knight, the textbook goblin, the generic fireball). It is executed well but could belong to many other projects.

**3–5 pts:** The sprite is a thinly disguised version of an existing trope or a near-copy of genre-standard visual shorthand. It brings no specific design decision that marks it as intentional.

**0–2 pts:** The sprite is indistinguishable from genre-stock work. No distinctive choice is present anywhere in the design.

#### Common Failure Patterns
- Defaulting to the "safe" version of a monster type (a green slime is a green slime — what makes *this* slime belong to *this* world?).
- Using reference images too literally — the sprite reproduces the reference's design language instead of interpreting it through the AM Pixel lens.
- Over-reliance on symmetry as a substitute for design — symmetrical characters tend to read as generic.
- Designing for technical correctness first and concept second — the sprite passes all automated checks but has no point of view.

---

### A6 — Soul / Visual Hierarchy · 5 pts

#### What Is Being Measured
This criterion is **context-dependent** based on the sprite's role in the scene:

- **Foreground assets (playable characters, named enemies, boss portraits):** Does the sprite have *personality and distinctiveness*? Does it feel like a specific individual rather than a type? Does visual hierarchy direct the eye to the most expressive element (usually the face or weapon)?
- **Background assets (ambient enemies, environmental sprites, crowd elements):** Does the sprite exhibit *visual recession*? Does it read as secondary — less contrast, simpler silhouette, lower detail density — so it does not compete with foreground elements for attention?

#### How a Human Reviewer Should Score This

Determine the sprite's scene role first. Then apply the appropriate lens:

**Foreground — Personality / Distinctiveness:**
- **5/5:** The sprite has a clear focal point. The design hierarchy leads the eye deliberately. If it's a character, there's an emotional read — you can guess its disposition from the sprite alone.
- **3–4/5:** Hierarchy is present but the focal point competes with secondary details. The character reads correctly but feels generic in personality.
- **0–2/5:** No hierarchy — all elements fight for attention equally. Or: the character reads as a placeholder with no emotional signal.

**Background — Visual Recession:**
- **5/5:** The sprite visually steps back without prompting. Lower contrast range, muted palette emphasis, simpler silhouette all confirm it as secondary. It enriches the scene without claiming attention.
- **3–4/5:** Mostly recessive, but one element (an overly bright color, an overly detailed outline) pulls forward.
- **0–2/5:** The sprite competes with foreground elements. It would need to be dimmed or resized in-engine to not distract.

#### Common Failure Patterns
- Foreground characters with no clear eye-lead — every limb and accessory rendered at equal detail weight.
- Background sprites given full-saturation colors from the character sub-palette — they visually advance instead of recede.
- Boss portraits where the weapon is more visually interesting than the face.
- Ambient enemies given the same outline weight as player characters — they don't read as secondary.

---

---

# RUBRIC B — Tilesets

## Gate Structure

Rubric B operates as a **single unified gate** — all criteria are scored by the same review pass (automated + human-assisted). There is no two-gate split.

```
Seam Integrity:          30 pts
Visual Recession:        20 pts
Texture Coherence:       20 pts
Atmospheric Consistency: 15 pts
Completeness:            10 pts
Technical Compliance:     5 pts
─────────────────────────────────
Total:                  100 pts
Passing threshold:       95/100
```

---

### B1 — Seam Integrity · 30 pts

**Tools:** Automated seam-tiling analysis (tile edge pixel comparison), visual tiling preview render

#### What Is Being Measured
Whether tiles in the set tile seamlessly in all valid arrangements — horizontal, vertical, and corner joins — without visible seam lines, pattern breaks, or edge artifacts. A seam is any visual discontinuity that the eye can trace as a grid line when the tileset is rendered at scale.

#### Scoring Scale
- **30/30 (Full):** No seam is detectable in any valid tile arrangement at native resolution. Edge pixels on all four sides of each tile match their neighbors across all tested layout patterns.
- **15–29 (Partial):** One or two tile pairs produce a faint but detectable seam. The majority of arrangements are seamless. The seams do not break scene-reading but are visible on inspection.
- **0/30 (Zero):** Any tile arrangement produces a clearly visible grid — seams trace the tile boundaries as a continuous line. Or: corner join artifacts are present in most tested arrangements.

#### Common Failure Patterns
- Designing tiles in isolation without previewing them tiled — edges don't account for what the neighbor tile contributes.
- Using a slightly different background color on edge pixels than interior pixels, creating a 1-pixel border effect when tiled.
- Texture elements (bricks, planks, stones) that align too regularly across tile borders — the repeat is detectable.
- Forgetting to test corner joins — horizontal and vertical seams pass, but the four-tile corner creates a visible artifact.
- Applying a subtle vignette or darkening to the tile edges during export.

---

### B2 — Visual Recession · 20 pts

**Tools:** Luminance variance analysis, saturation range check, foreground contrast comparison

#### What Is Being Measured
Whether the tileset reads as a background layer — lower contrast range, reduced saturation, simpler value structure than the foreground sprites that will be placed on it. Visual recession is not the same as "dark" — a snow tileset can be bright and still recede if its contrast range is compressed relative to character sprites.

#### Scoring Scale
- **20/20 (Full):** The tileset's luminance range and saturation values fall within the defined background tier. When a foreground sprite is composited over it, the sprite immediately reads as primary. No tile element is bright or saturated enough to compete with character outlines.
- **10–19 (Partial):** Most tiles recede correctly but one variant (e.g., a lit torch tile, a highlighted surface) advances enough to compete with foreground elements in some layout configurations.
- **0/20 (Zero):** The tileset's contrast range or saturation matches or exceeds the foreground tier. Sprites placed over it disappear or compete equally.

#### Common Failure Patterns
- Using full-palette character colors in environmental tiles — the environment visually steps forward.
- "Hero details" on tileset elements: hand-painted highlight spots with the same luminance as character highlight pixels.
- Forgetting that visual recession must survive both dark and light foreground sprites — testing only against one character skin.
- Animating a tile element (water shimmer, candle flicker) with high-contrast frames that periodically advance in the render stack.

---

### B3 — Texture Coherence · 20 pts

**Tools:** Pattern repetition analysis, texture frequency comparison across tile set

#### What Is Being Measured
Whether all tiles in the set share a unified texture language — consistent grain size, consistent surface detail density, consistent use of dithering vs. solid fills. A coherent tileset reads as one surface type; an incoherent one reads as tiles from different projects assembled together.

#### Scoring Scale
- **20/20 (Full):** Every tile in the set uses the same texture approach. Grain size is consistent. Dithering patterns (if used) share the same matrix and density. Surface detail complexity is equivalent across all variants.
- **10–19 (Partial):** Most tiles are coherent but one variant (e.g., a damaged or transition tile) uses a noticeably different texture density or dithering approach.
- **0/20 (Zero):** Multiple texture approaches coexist in the set without justification — some tiles use solid fills, others use dithering, others use detailed grain. The set looks assembled from disparate sources.

#### Common Failure Patterns
- Starting the set with one approach, then switching technique partway through when a tile proved difficult — early and late tiles use different methods.
- Transition or damage variants being treated as "special" and rendered with more detail than base tiles, breaking density consistency.
- Using dithering on one tile to solve a value problem and not applying it retroactively to the tiles that would benefit.
- Base tiles and animated variants having different texture resolution because the animated frames were scaled differently.

---

### B4 — Atmospheric Consistency · 15 pts

**Tools:** Color temperature analysis, palette mood cross-reference

#### What Is Being Measured
Whether the tileset's color relationships convey a consistent environmental mood — whether that is cold dungeon stone, warm interior wood, hostile volcanic rock, or any other defined scene atmosphere. Atmosphere is carried by color temperature, hue biases, and the relationship between warm and cool tones in the palette.

#### Scoring Scale
- **15/15 (Full):** The tileset's palette unambiguously conveys its defined atmosphere. Color temperature is consistent across all tiles. The hue relationship between light, midtone, and shadow is coherent and atmospheric (e.g., warm lights with cool shadows for candlelit stone).
- **8–14 (Partial):** Atmosphere is mostly present but one tile or variant pulls the temperature in an inconsistent direction — a cool tile in a warm set, or vice versa.
- **0/15 (Zero):** The tileset has no discernible atmospheric mood, or its color temperature contradicts the defined scene atmosphere (e.g., a cold dungeon tileset rendered with warm brown tones).

#### Common Failure Patterns
- Choosing tile colors by matching reference photos directly rather than selecting from the scene's atmospheric sub-palette.
- Shadow colors that are simply darker versions of the midtone rather than temperature-shifted — loses atmospheric depth.
- Transition tiles that use a neutral temperature to "blend" between two zones, accidentally stripping the atmosphere from the boundary region.
- Forgetting that animated tile variants (water, fire, lights) must remain within the same temperature range as static tiles.

---

### B5 — Completeness · 10 pts

**Tools:** Tile coverage checklist (defined per tileset type in project spec)

#### What Is Being Measured
Whether the tileset contains all required tile variants to support the layout system: floor fill, wall types (top, bottom, left, right, all four corners), transition variants, and any type-specific required tiles (water edge, door frame, etc.) as defined in the per-tileset spec.

#### Scoring Scale
- **10/10 (Full):** All required tiles are present and correctly tagged. No required variant is missing.
- **5–9 (Partial):** One or two required variants are missing or exist as rough placeholders. The tileset is functional for basic layouts but will produce holes in edge-case arrangements.
- **0/10 (Zero):** Core structural tiles are missing — the tileset cannot render a complete scene without obvious gaps.

#### Common Failure Patterns
- Submitting only the "easy" tile variants and deferring corner cases as "to be added later."
- Inner corner tiles missing — layouts render correctly in simple rectangles but break at concave corners.
- Transition tiles between two biomes submitted without corresponding tiles in the adjacent biome's set, making the transition one-directional.
- Placeholder tiles (solid color blocks) included in the set that were never replaced before submission.

---

### B6 — Technical Compliance · 5 pts

**Tools:** `palette_validator.py`, dimension/grid alignment check

#### What Is Being Measured
Whether all tiles conform to the project's technical specifications: correct pixel dimensions, correct grid alignment, all pixels on-palette, correct export format, and correct naming convention.

#### Scoring Scale
- **5/5 (Full):** Every tile is correctly dimensioned, on-palette, properly named, and in the correct export format.
- **3–4 (Partial):** Minor violation — one tile is misnamed, or one tile has a single off-palette pixel.
- **0/5 (Zero):** Systemic technical failures — wrong tile dimensions, wrong format, or majority of tiles have palette violations.

#### Common Failure Patterns
- Exporting the tileset as a single PNG sheet without slicing to individual tiles as required by the naming spec.
- Tile dimensions being 1 pixel off due to a crop error — the tile won't align on the grid.
- Off-palette pixels on tile edges introduced during the slice/export step.

---

---

# RUBRIC C — Parallax Battle Backgrounds

## Gate Structure

Rubric C operates as a **single unified gate** covering all layer and composition concerns.

```
Layer Seaming:              25 pts
Layer Depth Differentiation: 25 pts
Atmospheric Cohesion:        20 pts
Character Contrast:          15 pts
Emotional Tone:              10 pts
Technical Compliance:         5 pts
─────────────────────────────────────
Total:                      100 pts
Passing threshold:           95/100
```

---

### C1 — Layer Seaming · 25 pts

**Tools:** Layer edge continuity analysis, horizontal scroll seam check

#### What Is Being Measured
Whether each parallax layer tiles seamlessly on its horizontal scroll axis and transitions cleanly to adjacent layers vertically. Seams include: visible edges where the layer loops, visible color discontinuities at the layer's top or bottom edge where it meets the layer above or below, and pixel-level misalignment at the loop point.

#### Scoring Scale
- **25/25 (Full):** No seam is detectable at any loop point at native resolution. Layer top and bottom edges blend into adjacent layers without hard color breaks. The loop point is invisible during playback at the defined scroll speed.
- **13–24 (Partial):** The loop point is faintly detectable at one layer (visible as a subtle color or detail shift), or one layer edge has a minor hard transition to the adjacent layer.
- **0/25 (Zero):** Any layer has a clearly visible loop point during scroll, or a hard color break between layers is immediately obvious on first view.

#### Common Failure Patterns
- Painting the background in one canvas and slicing into layers after the fact — layer edges don't account for the scroll seam.
- Forgetting that the leftmost and rightmost pixel columns of each layer must match exactly for seamless horizontal looping.
- Layer bottom edges with a hard horizon line that doesn't blend into the layer below.
- Adjusting a layer's content after confirming the seam, breaking the previously tested loop point.

---

### C2 — Layer Depth Differentiation · 25 pts

**Tools:** Contrast tier analysis per layer, detail density comparison, scroll speed alignment check

#### What Is Being Measured
Whether the parallax stack reads as a convincing depth stack — distant layers must be lower contrast, lower saturation, lower detail density, and softer in value transitions than near layers. The depth illusion depends entirely on each layer being clearly distinguishable in visual weight from its neighbors. This criterion also checks whether the defined scroll speed for each layer matches its visual depth (slower = more distant).

#### Scoring Scale
- **25/25 (Full):** Each layer occupies a distinct contrast/detail tier. Viewing the stack in isolation, you can immediately rank the layers by depth without knowing the scroll speeds. Scroll speed assignments are consistent with the visual depth order.
- **13–24 (Partial):** Two adjacent layers are too close in contrast or detail density — they read as the same depth plane. Or: one layer's scroll speed is inconsistent with its visual weight (e.g., a high-detail layer scrolling slowly as if distant).
- **0/25 (Zero):** No discernible depth hierarchy in the layer stack — all layers read at the same visual weight, or the scroll speed order contradicts the visual depth order throughout.

#### Common Failure Patterns
- Designing all layers at full contrast and attempting to differentiate by hue alone — the depth read fails.
- Far-layer elements that are detailed (individual leaves, individual stones) when they should read as masses at distance.
- Near layers that are overly simple because they were designed last and rushed — they don't claim their visual weight in the stack.
- Forgetting that depth differentiation must survive both bright and dark scene lighting conditions.

---

### C3 — Atmospheric Cohesion · 20 pts

**Tools:** Cross-layer color temperature analysis, hue convergence check (fog/atmosphere simulation)

#### What Is Being Measured
Whether all layers share a unified atmospheric mood, and whether distant layers correctly exhibit atmospheric perspective — progressively shifting toward the background's dominant atmospheric color (fog, haze, sky tint) as layers recede. All layers must read as part of the same scene under the same lighting conditions.

#### Scoring Scale
- **20/20 (Full):** All layers share a consistent atmospheric color language. Distant layers show clear atmospheric perspective toward the defined horizon color. The full stack reads as one unified environment, not separate painted elements.
- **10–19 (Partial):** Atmosphere is mostly consistent but one layer breaks from the hue convergence — it reads as isolated from the scene's atmosphere.
- **0/20 (Zero):** No atmospheric cohesion across the stack — layers have incompatible color temperatures, or no atmospheric perspective is applied (all layers read as equally "in air").

#### Common Failure Patterns
- Each layer designed to look good in isolation — cohesion is an afterthought.
- Atmospheric haze applied as a multiply layer in a raster editor that introduces off-palette colors.
- Far layers that are simply desaturated rather than shifted toward the atmospheric color — desaturation without hue shift reads as washed-out, not distant.
- Mid-ground layers skipped in the atmospheric gradient — the jump from foreground to background feels discontinuous.

---

### C4 — Character Contrast · 15 pts

**Tools:** Foreground sprite composite test, luminance contrast measurement at character spawn zones

#### What Is Being Measured
Whether characters placed over the background at their defined spawn positions read clearly — specifically, whether the background's luminance values at those positions provide sufficient contrast against character outlines. The background must serve as a legible stage; it must not camouflage characters, make silhouettes unreadable, or compete with character color keys.

#### Scoring Scale
- **15/15 (Full):** All character types (light, dark, mid-tone) read clearly against the background at all defined spawn positions. No character outline merges with background elements. The background actively sets characters forward rather than absorbing them.
- **8–14 (Partial):** Most characters read clearly, but one character type (e.g., a dark-colored enemy) reads poorly against a specific background region. The issue is limited and positional.
- **0/15 (Zero):** Characters are significantly camouflaged against the background. Outline contrast falls below readable threshold across the majority of spawn zones, or the background's dominant color is too close to the character color keys for any character to read clearly.

#### Common Failure Patterns
- Designing the background without testing it with actual character sprites composited over it.
- Using a mid-grey background value that simultaneously absorbs both light and dark character silhouettes.
- High-frequency texture in the near layer (a detailed rock face, a patterned floor) that breaks up character outlines when seen together.
- Forgetting to test the boss zone specifically — boss characters are often larger and more colorful, requiring different contrast treatment.

---

### C5 — Emotional Tone · 10 pts

**Tools:** Human review (no automated tool)

#### What Is Being Measured
Whether the background conveys the correct emotional register for its defined battle context — threatening, melancholic, triumphant, ominous, peaceful, etc. as specified in the asset brief. Emotional tone is carried by color temperature, value arrangement (dark base vs. light base), line direction (horizontal calm vs. diagonal tension), and atmospheric density.

#### Scoring Scale
- **10/10 (Full):** The background communicates its defined emotional tone without ambiguity. A reviewer unfamiliar with the brief can identify the scene's mood accurately from the background alone.
- **5–9 (Partial):** The emotional tone is partially correct — the right general category (e.g., "dark and serious") but without the specific register (e.g., "melancholic" reads more as "threatening").
- **0/10 (Zero):** The background is emotionally neutral (no discernible tone) or conveys the wrong emotional register relative to the brief.

#### Common Failure Patterns
- Defaulting to generic "dark = serious" without considering the specific emotion — every difficult battle background looks the same.
- Overloading the background with too many competing emotional signals (dramatic lighting AND warm nostalgic tones AND threatening silhouettes) — they cancel each other out.
- Using color choices borrowed from reference scenes without checking that the borrowed tones carry the correct emotion in this context.
- Treating emotional tone as a color-only problem — ignoring composition, line direction, and value structure as emotional carriers.

---

### C6 — Technical Compliance · 5 pts

**Tools:** `palette_validator.py`, layer file structure check, dimension check per layer

#### What Is Being Measured
Whether all background layers conform to technical specifications: correct pixel dimensions per layer, all pixels on-palette, correct layer naming and export format, correct scroll speed metadata attached, and correct file structure (individual layer PNGs, not a flattened composite).

#### Scoring Scale
- **5/5 (Full):** All layers are correctly dimensioned, on-palette, properly named, and submitted with correct scroll speed metadata.
- **3–4 (Partial):** Minor violation — one layer is misnamed, or scroll speed metadata is missing from one layer but can be inferred from the file order.
- **0/5 (Zero):** Systemic failures — layers submitted as a flat composite, wrong dimensions, or majority of layers have palette violations.

#### Common Failure Patterns
- Flattening all parallax layers into one image before export — the scroll system cannot process a flat file.
- Forgetting to attach scroll speed metadata, leaving the implementation team to guess or default to wrong values.
- Layers exported at 2× or 0.5× of the target resolution due to canvas setup errors.
- Off-palette colors introduced by the atmospheric overlay step (see C3) when haze is applied as a raster blend instead of palette-matched color replacement.

---

---

# Batch Pass Rate — 99/100

## What This Means

The 99/100 batch pass rate is **not a point score**. It is a **quality floor for the entire production pipeline** and is tracked at the batch level, not the individual asset level.

**Definition:** In any batch of 100 evaluated assets (of the same rubric type), **99 or more must each independently score 95+ on their rubric**. One failure per 100 is the maximum acceptable defect rate. Two or more failures in a batch of 100 constitutes a pipeline failure.

## Why It Exists Separately

Individual pass/fail thresholds (95/100 per asset) establish whether a single asset ships. The batch pass rate establishes whether the *generation process itself* is under control. An agent or workflow that produces 90/100 assets at 95+ would pass every individual asset review but fail the batch rate — signaling systematic instability in some portion of the pipeline.

## How It Is Tracked

- Batches are defined per rubric type — 100 character sprites form one batch cohort; 100 tile sets form another.
- Each asset in the batch is scored independently. There is no averaging or pooling of scores.
- The batch pass rate is calculated after every 100 completions and reported as a pipeline health metric, not an individual asset score.
- A batch rate below 99/100 triggers a pipeline audit — root cause analysis of the failing assets to identify whether failures cluster around a single criterion (suggesting a tool miscalibration or a systematic design pattern error) or are random (suggesting a noise-level instability acceptable for remediation through individual rebuilds).

## What Counts as a Batch Failure

- 2 or more assets in 100 scoring below their rubric's passing threshold (95/100).
- Note: An asset that scores exactly 95 **passes**. An asset that scores 94 **fails**, regardless of how close it is to the threshold.
- Automated gate failures (Rubric A only) count as batch failures even though they never receive a final combined score — a sprite that cannot clear 85/85 automated is a failed asset.

## Remediation

- The one-failure-per-100 tolerance exists to allow for genuine edge cases — novel asset types that stress the rubric in unpredicted ways, or legitimate disagreement at the human gate boundary.
- A single failure does not trigger a process change. It triggers a rebuild of that asset only.
- Two or more failures per 100 trigger full pipeline audit before the next batch proceeds.

---

---

*AM Pixel Evaluation Rubric | Phase 1 Boot Training | v1.0*
