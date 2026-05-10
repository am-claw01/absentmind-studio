# AM Pixel — Proportion System
**Style Bible | Phase 2 | LOCKED**

---

## Overview

This document locks the canonical sprite dimensions for every context in AM Pixel. Proportions are not arbitrary — each system is tuned for **readability at actual playback scale** on modern displays rendering at 2× or 3× integer scale. Reference games (primarily *Final Fantasy VI* and *Chrono Trigger* on SNES, *Final Fantasy IV*, and *Secret of Mana*) are cited for each context to ground design decisions in proven practice.

**Core principle:** Pixel art proportions are a communication tool, not an aesthetic preference. The correct ratio is the one that conveys the most information at the smallest size without ambiguity.

---

## 1. WORLD SPRITE (Overworld / Field Exploration)

### Canonical Dimensions
- **Canvas:** 16 × 24 px
- **Usable figure area:** 16 × 22 px (1 px gutter top and bottom for animation clearance)
- **Displayed at:** 2× integer scale = 32 × 48 screen pixels; 3× = 48 × 72 screen pixels

### Head-to-Body Ratio
- **Head:** 8 × 8 px (one-third of total canvas height)
- **Torso + arms:** 8 × 8 px
- **Legs + feet:** 8 × 6 px
- **Ratio:** 1 : 2 (head to remaining body) — a mild chibi lean for tile-map readability

### Limb Proportion Conventions
- **Arms:** 2 px wide, approximately 6 px long when extended; typically visible as short stubs in forward-facing idle
- **Hands:** 2 × 2 px block — no finger detail at this scale
- **Legs:** 3–4 px wide each, 5–6 px tall; slight taper toward foot (3 px at knee, 2 px at ankle)
- **Feet:** 2 × 2 px nub; footwear indicated by color only, not shape

### Overlay Grid Template
```
+----------------+   16px wide
|   [ HEAD  ]    |   Row 1–8:   Head zone (8px tall)
|   [TORSO  ]    |   Row 9–16:  Torso zone (8px tall)
|   [ LEGS  ]    |   Row 17–22: Leg zone (6px tall)
|                |   Row 23–24: Animation clearance / shadow dot
+----------------+
```
- Center axis: Column 8–9 (character center at pixel 8.5)
- Foot contact line: Row 22

### Why This Works at Playback Scale
At 2× scale the 16×24 sprite renders as 32×48 on-screen pixels. The 8px head becomes a 16px rendered head — just large enough to show hair color, a distinguishing hat or horns, and eye color (a single-pixel pair). The 1:2 head-body ratio ensures characters are distinguishable from one another even when 4–6 sprites crowd a tile cluster. A more realistic 1:4 ratio at this canvas size would reduce the head to 4–5px — too small for any personality read.

### SNES Reference
*Final Fantasy VI* field sprites are 16×24 px with similarly chibi proportions — Terra, Locke, and all playable characters fit this exact canvas. Heads are approximately 8×8 and the ratio holds. *Chrono Trigger* field sprites are also 16×24 but lean slightly more realistic (head ~7px, slightly taller legs) — CT prioritizes silhouette variety over pure readability, which is a valid alternative but AM Pixel locks the FF6-leaning system for consistency.

---

## 2. BATTLE SPRITE (Combat / Side-View)

### Canonical Dimensions
- **Player Character Canvas:** 32 × 48 px
- **Usable figure area:** 30 × 46 px (1 px gutter on all sides)
- **Displayed at:** 2× scale = 64 × 96 screen pixels; 3× = 96 × 144 screen pixels

### Head-to-Body Ratio
- **Head:** 10 × 12 px (roughly one-quarter of total canvas height)
- **Neck + Torso:** 10 × 14 px
- **Hips + upper legs:** 10 × 12 px
- **Lower legs + feet:** 10 × 10 px
- **Ratio:** 1 : 3 to 1 : 3.5 (head to total body) — a semi-heroic, slightly stylized proportion

### Limb Proportion Conventions
- **Arms:** 4–5 px wide at shoulder, taper to 3 px at forearm; total arm length ~16 px when extended
- **Hands:** 3 × 4 px — enough to suggest grip shape on a weapon hilt
- **Legs:** 5–6 px wide at thigh, taper to 4 px calf, 3 px ankle
- **Feet / footwear:** 5 × 3 px — boot shape is now readable and character-identifying
- **Weapon overlays:** Weapons are drawn as separate pixel layers on top of the sprite, not embedded — canvas extends to 40 × 48 for weapon clearance on right-facing fighters

### Overlay Grid Template
```
+--------------------------------+   32px wide
|        [  HEAD  10x12 ]        |   Row 1–12:  Head zone
|        [ NECK  10x4   ]        |   Row 13–16: Neck / collar
|    [ARM][ TORSO 10x10 ][ARM]   |   Row 17–26: Torso + arms (arms extend 6px L/R)
|        [ HIPS  10x8   ]        |   Row 27–34: Hips / belt zone
|        [ THIGH 10x8   ]        |   Row 35–42: Upper leg
|        [ LOWER 10x6   ]        |   Row 43–48: Calf + foot
+--------------------------------+
```
- Center axis: Column 16–17
- Ground contact line: Row 47–48
- Weapon zone: Columns 1–8 (off-hand) and 25–32 (sword arm)

### Why This Works at Playback Scale
The 32×48 canvas at 2× becomes a 64×96 rendered sprite — large enough for expressive facial features (single-color eye area, eyebrow pixel, mouth state), visible armor detail like pauldrons and belt buckles, and readable hand/weapon grip. The 1:3 ratio reads as "young adult adventurer" — less exaggerated than field sprites but not hyper-realistic. At 3× scale (the premium display mode), individual hair strands, scarf wraps, and sheathed weapon detail become legible. The slightly wider torso (10px) vs. head (10px same width) gives battle sprites a solid, grounded stance.

### SNES Reference
*Chrono Trigger* battle sprites (player characters) are drawn at approximately 32×48 with a 1:3 head-body proportion. Crono's head is ~10px tall, his body fills the remaining 38px in two zones (torso and leg). *Final Fantasy VI* battle sprites are smaller — approximately 24×24 for standard characters — but FF6 uses a more abstract, icon-like battle presentation. AM Pixel adopts the CT sizing for its richer expressivity. *Secret of Mana* character sprites are a useful third reference: slightly squarer (32×40), with rounder heads, but the limb taper convention is identical.

---

## 3. CHIBI / GLOBAL MAP SPRITE

### Canonical Dimensions
- **Canvas:** 8 × 8 px (single tile) — can extend to 8 × 10 px for characters with tall hats or wings
- **Displayed at:** 2× = 16 × 16 screen pixels; 3× = 24 × 24 screen pixels

### Head-to-Body Ratio
- **Head zone:** 5 × 5 px (nearly the entire sprite)
- **Body stub:** 3 × 3 px (icon-level abstraction)
- **Ratio:** Nearly 1 : 1 — pure chibi for global map legibility

### Limb Proportion Conventions
- No discrete limbs at this scale — legs are a 2–3 px wide base block
- Arm pixels are omitted in idle; appear as a 1px extension for directional animation frames
- Character identity is conveyed by **silhouette + color alone**: hat shape, hair color, armor color
- Each character should have a unique 1–2 pixel color signature visible on the head zone

### Overlay Grid Template
```
+--------+   8px wide
|[HHHHH ]]   Row 1–5:  Head zone (hair, hat, face color)
|[ BODY ]]   Row 6–8:  Body / leg stub
+--------+
```
- Face indicated by skin tone color patch — 2 × 2 px or 3 × 2 px
- No outline on body zone; silhouette must read from color contrast alone

### Why This Works at Playback Scale
At 2× scale, 8×8 becomes 16×16 — a standard UI thumbnail. The global map is a zoom-out view; a 16-screen-pixel sprite at a typical RPG global zoom represents a character covering enormous geographic distance. The chibi ratio (huge head relative to body) is not a stylistic affectation — it is the only way to preserve character identity at this size. The head must be large enough to show hair color and a hat, which are the primary identifiers. A more realistic ratio would produce a 3px head where hair, skin, and hat are indistinguishable.

### SNES Reference
*Final Fantasy VI* world map sprites are literal 8×8 single tiles (the "walking chibi" mode on the overworld). Characters are almost pure head with a small colored leg block. *Chrono Trigger* uses a similar system, slightly more refined at 8×10 with a slightly longer leg region. Both games rely exclusively on hat and hair color for character identification at this scale, which is why every CT/FF6 character has a visually distinct color signature from the first pixel.

---

## 4. PORTRAIT ART

### Canonical Dimensions
- **Canvas:** 56 × 56 px
- **Displayed at:** 1× (native) or 2× = 112 × 112 screen pixels; typically shown in dialogue boxes

### Head-to-Body Ratio
- **Face + hair area:** ~32 × 40 px (centered in canvas, starting row ~5)
- **Neck + shoulder stub:** ~32 × 16 px (lower canvas)
- Portrait shows head and upper chest only — ratio is irrelevant as a full-body measurement; face fill is the design goal

### Limb Proportion Conventions
- Arms and torso are partially visible as shoulder/collar area
- Armor, collar, and costume trim are visible on the shoulder region (rows 40–56)
- Hands are not shown in portrait context

### Overlay Grid Template
```
+--------------------------------------------------------+   56px wide
| [  HAIR / HAT ZONE — full width, rows 1–12           ] |
| [  FACE ZONE — centered ~32px wide, rows 8–40        ] |
| [  EYE ROW — rows 16–22, eyes at columns 14–20/34–40 ] |
| [  NOSE — rows 25–28, col 26–30                      ] |
| [  MOUTH — rows 32–36, col 22–34                     ] |
| [  NECK + COLLAR — rows 40–50                        ] |
| [  SHOULDER TRIM — rows 48–56, full width            ] |
+--------------------------------------------------------+
```
- Face center: Column 28
- Eye separation: approximately 12 px between inner corners
- Hair extends to canvas edges and can bleed outside the face zone

### Why This Works at Playback Scale
At native 1× during dialogue, the 56×56 portrait sits in the corner of a dialogue box. The face occupies most of the canvas (32×40 within 56×56 = ~57% coverage) rather than being centered with excessive hair padding, because the face is the communication vehicle — expression, emotion, and identity. At 2× the portrait reads as 112×112, enough to show iris detail (2×2 px colored circle inside a 4×4 white area), wrinkle or war-paint detail on cheeks, and individual teeth in an open-mouth expression. The shoulder area anchors the portrait in physical space and conveys class/role identity through armor or robe trim.

### SNES Reference
*Final Fantasy VI* portrait tiles are 48×48 assembled from a 3×3 tilemap of 16×16 tiles. The face fill ratio is very high — characters' hair often bleeds to the canvas edge. AM Pixel uses 56×56 to gain an extra ring of hair/framing pixels and a more visible shoulder region. *Chrono Trigger* uses 88×88 portraits (larger dialogue boxes) with a similar face-dominant approach. AM Pixel's 56×56 is the midpoint — more detailed than FF6, more compact than CT.

---

## 5. NPC VARIANTS

### Standard NPC
- **Canvas:** 16 × 24 px — identical to World Sprite
- All World Sprite proportion rules apply (see §1)
- NPC characters use a reduced palette of 3 shades (vs. 4 for player characters) to visually subordinate them on-screen

### Seated / Partial NPC
- **Canvas:** 16 × 16 px
- Shows torso up (above table or desk), using only the Head (8×8) and upper Torso (8×8) zones
- Used for shopkeeper windows, classroom scenes, NPC-behind-desk contexts

### Crowd / Background NPC
- **Canvas:** 8 × 16 px — half-width, full-height
- Extremely simplified silhouettes: solid color masses, no detail
- Used in crowd scenes, background villager groups, festival scenes
- Designed to be tiled and color-varied without reading as player characters

### Child NPC
- **Canvas:** 12 × 18 px (non-standard — exception to the 8px grid rule)
- Head: 8 × 8 px (same as adult — children read small by having a short body)
- Legs: only 4 px tall (vs. 6 px in adult)
- Arms: 1 px wide stubs
- The large head / short leg system is the universal visual shorthand for "child" at small scale

---

## 6. ENEMY SPRITES

### Usage Rules
- Enemy sprites are sized relative to narrative threat level and in-world scale, not arbitrary hierarchy.
- All enemies must fit within their defined canvas, including attack animation frames.
- Hit flash and damage states use palette-cycling on the existing sprite — no extra canvas budget.

---

### ENM-S · Small Enemy

- **Canvas:** 16 × 16 px
- **Examples:** Slimes, bats, small insects, rat-type creatures, will-o-wisps
- Head-to-body: Usually a single unified body mass (no distinct head), or a 1:1 ratio for humanoid small enemies
- Limbs: 1–2 px stubs if present; many small enemies are blob or sphere forms
- **Why 16×16:** Small enemies in a battle row need to visually recede. 16×16 at 2× = 32×32 screen pixels, which is roughly half the height of a player character battle sprite. This size difference communicates "low threat" and "cannon fodder" without a word of UI text.

---

### ENM-M · Medium Enemy

- **Canvas:** 32 × 32 px
- **Examples:** Soldiers, undead warriors, mid-tier monsters, golems, large beasts
- Head-to-body: 1:2.5 for humanoid enemies (same semi-heroic read as player battle sprites, slightly less refined)
- Limbs: 4–6 px wide; stylized but immediately readable in shape
- **Why 32×32:** Matches the width of a player character battle sprite, establishing "peer-level threat." The square canvas (vs. the player's 32×48 vertical rectangle) makes medium humanoid enemies look stockier and more intimidating despite a similar pixel area.

---

### ENM-L · Large Enemy

- **Canvas:** 48 × 48 px
- **Examples:** Large monsters, animated constructs, guardian creatures, elite enemies
- Head-to-body: 1:4 or less — large enemies de-emphasize the head in favor of a imposing body mass
- Limbs: Thick, 8–10 px limb blocks; stumpy and powerful
- Silhouette must read at a glance: a distinctive outline shape (horns, wide shoulders, trailing cloak) is required at this size class
- **Why 48×48:** At 2× this is 96×96 screen pixels — visibly larger than any player sprite but still contained within a standard battle background without dominating the entire screen. The 48px square gives room for a genuinely imposing silhouette with meaningful detail.

---

### ENM-B · Boss Enemy — Multi-Tile System

- **Base canvas unit:** 16 × 16 px tiles assembled into a grid
- **Standard Boss:** 2×2 tile assembly = **32 × 32 px effective canvas**
- **Large Boss:** 3×3 tile assembly = **48 × 48 px effective canvas**
- **Mega Boss:** 4×4 tile assembly = **64 × 64 px effective canvas**
- **Screen-spanning Boss:** 4×6 tile assembly = **64 × 96 px effective canvas** (maximum)

#### Multi-Tile Assembly Rules

1. **Tile seams must be invisible.** Sprites must be drawn as a complete image first, then sliced. Never design per-tile — design the whole boss, then cut.
2. **Each tile is independently animatable.** Assign each tile a layer index. Breath attacks, arm-wave animations, and phase-shift effects animate one tile group at a time using the full SNES sprite system.
3. **Segmentation strategy by boss type:**
   - Horizontal cut (2×1, 4×1): Best for wide serpents, dragons, and horizontal sweepers
   - Vertical cut (1×2, 1×3): Best for tall pillars, standing giants, and ascending forms
   - Grid cut (2×2, 3×3): Best for compact powerful bosses (armored knights, stone titans, mechanical constructs)
   - Irregular cut: Some bosses have limbs as separate tile clusters (detached arms, floating orb satellites) — treat limb tiles as independent sprite objects with their own animation index
4. **Maximum usable canvas:** 64 × 96 px (4×6 tiles). Beyond this, the boss occupies the full battle screen background and is handled as a background layer overlay, not a sprite system.
5. **Palette constraint:** Each 16×16 tile uses 1 SNES sub-palette (16 colors including transparent). A 4×4 boss uses 4 distinct sub-palettes, rotated in pairs. Plan palette segment boundaries before drawing.
6. **Hit detection zone:** Define a single logical hitbox tile or tile group (typically the torso or core tile). All hit flash effects apply to this zone first, then propagate outward with a 1–2 frame delay for visual read.

#### Boss Overlay Grid Template (3×3 example — 48×48 px)

```
+----------------+----------------+----------------+   48px wide
|  TILE [0,0]    |  TILE [1,0]    |  TILE [2,0]    |  Row 1–16:  Top third
|  (L shoulder / |  (head /       |  (R shoulder / |
|   claw / horn) |   crown / eye) |   wing / arm)  |
+----------------+----------------+----------------+
|  TILE [0,1]    |  TILE [1,1]    |  TILE [2,1]    |  Row 17–32: Mid third
|  (L torso /    |  (chest core / |  (R torso /    |
|   arm / wing)  |   crest / gem) |   weapon arm)  |
+----------------+----------------+----------------+
|  TILE [0,2]    |  TILE [1,2]    |  TILE [2,2]    |  Row 33–48: Bot third
|  (L leg /      |  (abdomen /    |  (R leg /      |
|   root / tail) |   pelvis / fx) |   root / tail) |
+----------------+----------------+----------------+
```

- [1,1] center tile = PRIMARY hit zone + core palette anchor
- Corner tiles [0,0] [2,0] [0,2] [2,2] = secondary animation tiles
- Edge tiles [1,0] [0,1] [2,1] [1,2] = phase-transition tiles (first to change in boss transformations)

### SNES Reference — Boss Multi-Tile
*Final Fantasy VI* implements every major boss as a multi-sprite assembly. Ultros uses a 3-tile wide horizontal arrangement; the Atma Weapon is a 2×3 grid; Kefka's final form stacks multiple independent sprite layers that animate separately. The key FF6 insight: **tile independence enables phased destruction animations** — a boss loses a limb tile when defeated, revealing an alternate tile beneath. AM Pixel's system formalizes this tile-index approach. *Chrono Trigger* similarly uses assembled multi-sprite bosses (Lavos Core is three separate 32×32 sprites arranged laterally). CT's contribution is the **satellite limb pattern** — detachable boss parts that orbit or float independently and must be defeated separately.

---

## 7. PROPORTION COMPARISON AT PLAYBACK SCALE

The following table shows the rendered screen pixel size of each sprite type at 2× and 3× integer scale:

| Sprite Type | Canvas | 2× Screen | 3× Screen |
|---|---|---|---|
| Chibi / Global Map | 8 × 8 | 16 × 16 | 24 × 24 |
| World / Field | 16 × 24 | 32 × 48 | 48 × 72 |
| Battle (Player) | 32 × 48 | 64 × 96 | 96 × 144 |
| Portrait | 56 × 56 | 112 × 112 | 168 × 168 |
| Enemy Small | 16 × 16 | 32 × 32 | 48 × 48 |
| Enemy Medium | 32 × 32 | 64 × 64 | 96 × 96 |
| Enemy Large | 48 × 48 | 96 × 96 | 144 × 144 |
| Boss Max | 64 × 96 | 128 × 192 | 192 × 288 |

The 2× and 3× columns represent the visible display footprint in a modern window at common handheld (3×) and desktop (2× or 3×) scales. Design decisions for linework weight, color ramp step count, and detail density are calibrated for the **2× column** as the primary quality target. The 3× column is the aspirational read.

---

## 8. ANIMATION FRAME BUDGET PER CONTEXT

Dimensions determine not just visual design but animation cost. The following budgets are canonical:

| Sprite Type | Idle Frames | Walk Cycle | Action / Attack | Hit / Death |
|---|---|---|---|---|
| Chibi Map | 2 | 4 | — | 1 |
| World | 2–4 | 4–8 | 3–4 (use/interact) | 2 |
| Battle (Player) | 2 | — | 4–6 | 3 |
| Portrait | 1 (base) | — | 2–3 (expression) | — |
| NPC Standard | 2 | 4 | 1 (react) | — |
| Enemy Small | 2 | 2–4 | 3 | 2 |
| Enemy Medium | 2–4 | 4 | 4–6 | 3 |
| Enemy Large | 2 | — | 4–8 | 4 |
| Boss | 4 | — | 6–10 | 6 (phase cascade) |

Boss "phase cascade" death: each tile group fades or shatters in sequence over 6 frames, giving the death animation a spatial spread across the full boss canvas.

---

## 9. CROSS-CONTEXT IDENTITY CONSISTENCY

Characters appear in multiple contexts (global map → field → battle → portrait). The following rules maintain consistent identity across the size jump:

1. **Color signature is canonical.** A character's primary hair color, armor color, and skin tone must be identical (same palette ramp) across all contexts. If Lirien has teal hair in battle sprites, her 8-pixel global map dot must use that same teal.
2. **Silhouette element must survive the shrink.** Every character must have one silhouette feature (a hat brim, a horn, an oversized sword on the back, a distinctive collar) that reads at 8×8. Design this first, not last.
3. **Head zone proportions bridge the jump.** The World Sprite's 8×8 head becomes the Battle Sprite's 10×12 head. The same color block areas expand — they do not rearrange. The artist is drawing the same face at a larger resolution, not a new character.
4. **Portrait extends Battle Sprite.** The 56×56 Portrait is a zoomed-in crop of the Battle Sprite's head + upper torso, redrawn at native resolution for clarity. It should feel like the same person the player has been looking at in battle, not a more realistic or more stylized version.

---

*AM Pixel Proportion System | Style Bible v1.0 | LOCKED*
