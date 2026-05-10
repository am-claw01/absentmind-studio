# AM Pixel — Lighting Standard
**Style Bible | Phase 2 | LOCKED**

---

## Table of Contents

1. [Overview & Purpose](#overview--purpose)
2. [Default Light Source: Top-Left](#default-light-source-top-left)
3. [Applying Top-Left Lighting](#applying-top-left-lighting)
4. [Environment Lighting Variants](#environment-lighting-variants)
5. [Shadow Placement Rules](#shadow-placement-rules)
6. [Light & the Hue-Shifted Ramp System](#light--the-hue-shifted-ramp-system)
7. [Specular & Highlight Placement by Material](#specular--highlight-placement-by-material)
8. [Common Lighting Mistakes](#common-lighting-mistakes)
9. [Battle Background Lighting & Layer Depth](#battle-background-lighting--layer-depth)

---

## 1. Overview & Purpose

This document locks the lighting conventions for all visual assets in the AM Pixel project — character sprites, tilesets, UI elements, parallax backgrounds, and battle scenes. Consistent light direction is the single most powerful tool for making a pixel art game read as a unified visual world. An inconsistent light source breaks object-level believability even when individual assets look polished in isolation.

All artists must apply these rules to every asset they produce. Any environment-specific deviation from the default is documented in Section 4. If a lighting scenario is not covered here, flag it before shipping the asset — do not invent a convention.

---

## 2. Default Light Source: Top-Left

### 2.1 Canonical Direction

The AM Pixel project uses a **top-left light source** as its global default. This is expressed as approximately a **10 o'clock angle** — not directly overhead, not directly to the left, but biased slightly toward the top.

```
Light source angle: ~315° (top-left, counterclockwise from right)
Elevation: ~45° above the horizon plane
```

This is the canonical SNES RPG lighting convention, used in Chrono Trigger, Final Fantasy VI, and Secret of Mana. It is deliberately classical.

### 2.2 What This Means Practically

- **Top faces** of forms receive the most light — the tops of heads, shoulders, hats, flat horizontal surfaces
- **Left faces** of forms are lighter than right faces for vertically-oriented surfaces
- **Bottom and right faces** are in shadow
- **Underlighting** (light from below) is **never** the default and only occurs in specific fire/lava environments (see Section 4)

### 2.3 The "Floor Rule"

For overhead-angled sprites in a top-down or ¾ perspective context:
- The top of the sprite (the part of the character that would be furthest from the viewer in a ¾ view) receives slightly more light due to the downward angle of the source
- Do not confuse "top of the screen" with "top of the form" — keep thinking in 3D space even when working in 2D pixels

---

## 3. Applying Top-Left Lighting

### 3.1 Character Sprites

**Head:**
- Highlight sits on the **upper-left quadrant** of the head — top of the skull, upper-left of the face
- The right cheek and jaw fall into mid-shadow
- The underside of the chin, if visible, is the darkest face of the head
- Eyes: The upper eyelid catches light; the iris sits in partial shadow from the brow. A 1px specular dot on the iris belongs on the **upper-left** of the iris, not centered

**Torso:**
- Left shoulder: brightest point on the upper body after the head
- Right shoulder: one ramp step darker than left
- The left side of the torso wall: lighter
- The right side of the torso wall: darker
- The chest facing the viewer (front face): mid-tone — it is neither the lightest nor the darkest face
- Stomach / lower torso: gradient toward shadow as it curves away from the light and toward the ground

**Arms:**
- Upper arm cylinder: bright on the upper-left surface, shadow on the lower-right underside
- Forearm: same rule — the shadow wraps around the bottom of the cylinder
- Gauntlets and armor on arms follow the same logic but may have sharper ramp transitions due to hard surfaces (see Section 7)

**Legs:**
- Thighs: lit on the top-left surface, shadowed on the inner and lower faces
- The gap between the legs generates **contact shadow** — the inner thigh faces are among the darkest areas on the lower body
- Feet/boots: the top of the foot is lit; the sole is in shadow (rarely visible but important for large sprites)

**Hair:**
- Hair is not a smooth form — treat it as a collection of clumped masses, each independently lit
- Each clump: brightest pixel on its upper-left face, darkest at its base where it contacts the scalp or the clump below
- Do not globally light the whole hair mass as one form; it reads as a helmet

### 3.2 Tilesets

**Ground tiles (floor, grass, dirt, stone paving):**
- Ground tiles in a ¾ view primarily face upward → they receive near-full light
- Variation comes from texture detail, not dramatic shading
- Tile-to-tile transitions use the palette's natural texture ramps, not light direction changes
- Raised edges on cobblestone or brick: the **top edge and left edge** of the raised stone catch highlight; the **right edge and bottom edge** fall in shadow

**Wall tiles:**
- Vertical walls facing the viewer (south-facing in ¾ perspective): mid-tone, treated as the "front" face
- Walls facing left (west-facing): lighter — they catch the top-left source
- Walls facing right (east-facing): darker — they face away from the source
- Wall tops (horizontal caps): lit — treat as a top face

**Object tiles (trees, barrels, chests, furniture):**
- Every object tile must be treated as a 3D form and shaded with the top-left source, even when sitting on the floor
- Cylinders (barrels, pillars, tree trunks): highlight on the upper-left arc, shadow on the lower-right arc
- Spheres (tree canopies, round objects): highlight offset to upper-left, shadow graduating toward lower-right and bottom

**Cliff / elevation tiles:**
- Top surface: fully lit
- Left face of the cliff: lighter shadow (some light wraps from source)
- Right face of the cliff: deepest shadow
- Bottom of the cliff: in shadow; use the darkest ramp step

### 3.3 UI Elements

UI does not exist in the game world, but it must still follow a visual logic for consistency and readability.

- **Panels and windows:** Treat as a slightly raised flat surface. Top and left edges of panels receive a 1px highlight; bottom and right edges receive a 1px shadow. This simulates the top-left source raising the panel off the screen surface.
- **Buttons and icons:** Same bevel logic — lit top-left edge, shadowed bottom-right edge.
- **Text boxes:** Background fill is neutral (per MASTER_PALETTE UI tier); the border follows the bevel convention.
- **Icons and item sprites:** Item icons must obey the top-left source exactly as character sprites do. A sword icon should show the same lighting as if it were a 3D sword model lit from the top-left. Do not center-light icons.
- **HP/MP bars:** The fill of the bar is lit; a 1px shadow at the bottom of the bar's interior simulates depth.

> **Rule:** UI elements must never introduce a conflicting light direction. The top-left convention applies even to menu decorations and ornamentation. A chandelier icon in a UI border should still show top-left lighting.

### 3.4 Parallax Layers

Parallax background layers follow modified lighting rules because they are landscape elements at distance, not objects the player interacts with.

- **Distant sky / far background layers:** Do not apply object-level shading. Color temperature and value do the work of expressing light. Bright toward the light source's screen region (upper-left); cooler and dimmer toward the opposite corner.
- **Mid-distance architecture or terrain:** Apply soft top-left shading — tops of structures are lighter, right-facing sides are darker — but use only 2 ramp steps maximum (not the full 3–4 ramp used on close sprites). Distance reduces contrast.
- **Near-background decorative elements (trees, pillars, cliffs at screen edge):** Full top-left shading, same as foreground tilesets, to maintain parallax depth separation. These should read as "part of the world" rather than painted backdrops.

---

## 4. Environment Lighting Variants

Each environment variant **overrides the default** in specified ways only. Everything not listed as overridden continues to follow the top-left default.

### 4.1 Caves

**Light Character:** Dark ambient, warm point sources from torches/crystals.

- **Ambient light:** Significantly reduced. The mid-tone in the sprite palette functions as the effective shadow color in caves — what is "mid" outdoors reads as "lit" indoors.
- **Torch point sources:** Placed in the scene as tile objects. Any sprite or tile within ~3–4 tiles of a torch receives a **warm tint** (shift the active ramp toward the warm variants; see Section 6 for ramp interaction rules).
- **Light direction near torches:** Torches are roughly at character height or below — light emanates in all directions, but the dominant falloff is **outward and upward from the torch**. Characters standing directly beside a torch may show underlighting on their lower face.
- **Areas away from torches:** Use the base palette's darkest ambient ramp. No top-left highlight — ambient is too low to generate directional shading. Forms read primarily as silhouettes softened by the ambient level.
- **Crystal/magic light sources:** Same rules as torches, but color temperature shifts to the light's hue (blue crystal = cool blue tint on nearby surfaces).

> **Cave rule:** Never add a top-left highlight in a dark cave area far from a light source. The highlight implies a light source that doesn't exist in the scene.

### 4.2 Underwater

**Light Character:** Cool diffuse, light shafts from above, all direction from above-slightly-left.

- **Ambient:** Diffuse and cool. Blue-green shift on all surfaces. The warm ramp variants are not used underwater except for fire-based objects (which have their own underwater visual treatment).
- **Direction:** Light still comes broadly from above (sunlight through water), but the diffusion means there is no sharp highlight. Use only the **top face** as lit — left-face advantage is reduced to a single ramp step or eliminated.
- **Caustic patterns:** If caustic light patterns are added to floor tiles, they are an engine-side effect, not drawn per-frame in the tile art. Tile art provides the base shading; caustics are layered on top.
- **Depth fade:** Objects deeper in the scene (further from the water surface) receive a progressively cooler and darker tint. Near-surface objects have the most color; deep objects approach a single-tone blue-grey.
- **Character sprites in water:** When a character sprite is shown submerged, the top of the sprite may receive a very subtle light shift upward (toward lighter, cooler). The underside receives no underlighting — the water diffuses the upward bounce.

### 4.3 Night / Outdoor

**Light Character:** Cool, dim, dominant source from top-right (moon).

- **Primary source:** Moon repositioned to **top-right** (~1–2 o'clock). This is the only scenario where the canonical top-left source is fully replaced by an overriding directional source.
- **Color temperature:** Cool — pale blue-white moonlight. Shift ramps toward cool variants (see Section 6).
- **Highlights:** Now appear on the **upper-right** face of forms. Left-facing surfaces are now in shadow relative to the moon.
- **Secondary fill light:** Optional. A faint warm glow from ground-level sources (campfire, city lights on the horizon) may provide a very subtle uplift on the shadowed (left) faces. This is fill, not a second directional source — it should read as ambient, not as a distinct highlight.
- **Stars and sky:** Sky tiles at night use a fixed color, not the top-right logic. Stars are static decorative elements.

> **Night rule:** Flip your lighting mental model. Top-right is lit, bottom-left is shadow. Check every tile and sprite used in a night exterior scene for correct moonlight directionality.

### 4.4 Interior — Firelight

**Light Character:** Warm, flickering point source from low center or below.

- **Source position:** Fireplace, brazier, or central lamp, typically at or below character waist height.
- **Light direction:** **From below**, or from the direction of the fire object in the scene. This is deliberately dramatic.
- **Underlighting on characters:** The underside of the chin, the undersides of arms and hands, the belly — these areas are lit. The top of the head and shoulders receive less light and fall slightly into shadow.
- **Color temperature:** Warm orange-amber shift on the lit faces. The shadow faces (upper/top) take on a cool complement — use the cool ramp variants for shadow in firelight, warm variants for light.
- **Flicker:** Flicker is an engine effect (cycling between 2–3 brightness levels of the light radius). The sprite art itself does not animate for flicker — the engine handles it via tint or palette cycle.
- **Walls and floor:** Bottom portions of walls receive the fire's warm light. Upper walls are in relative shadow. The floor around the fire source is the brightest surface.

---

## 5. Shadow Placement Rules

Three types of shadow are used in AM Pixel. Each has a distinct role and must not be confused with the others.

### 5.1 Form Shadows

Form shadows are the **shaded faces of a 3D form** — the parts of an object that turn away from the light source. They are drawn directly into the sprite's pixel art using the darker ramp steps.

- Arise from the top-left light source direction
- Are the primary shading tool for all character sprites and tiles
- Transition from mid-tone to shadow using **1–2 ramp steps** — never jump from the lightest to the darkest in a single pixel
- Follow the curvature of the form: a rounded edge has a gradual step from light to shadow; a sharp corner has an abrupt step

### 5.2 Cast Shadows

Cast shadows are the **shadow a form throws onto another surface** (e.g., a character's shadow on the floor, a tree's shadow on the grass).

- Cast shadows fall **to the lower-right** in the default top-left lighting scenario
- They are **not** the same as the character's contact shadow (see 5.3)
- Cast shadows on the ground in overworld contexts: simplified to 1–2 pixel-wide ellipse beneath the character's feet, or an elongated dark ellipse stretched toward the lower-right
- Cast shadows from large objects onto walls or terrain: drawn as simplified dark fills, using the darkest ramp step for the affected tile, without complex shape tracing
- Rule: Cast shadow shapes are **simplified**, not photorealistic. Prioritize read clarity over accuracy.

**Cast shadow direction by environment:**

| Environment | Cast Shadow Direction |
|---|---|
| Default outdoor (day) | Lower-right |
| Cave (torch) | Away from torch position |
| Underwater | Minimal / diffuse, not strongly directional |
| Night (moon top-right) | Lower-left |
| Interior firelight | Away from fire source, toward upper area |

### 5.3 Contact Shadows

Contact shadows are the **darkening where one form meets or sits on another surface** — the underside of a foot touching the ground, the base of a wall meeting the floor, the neck meeting the collar.

- Always present regardless of light direction — contact shadows are caused by occlusion, not by the light source direction
- Use the darkest 1–2 ramp steps for contact shadow
- 1–2px wide at most for character-scale sprites
- Must be consistent: if a character has a contact shadow on the floor in one scene, they must have it in all scenes (exception: UI / floating menu sprites)
- Contact shadow remains even in the night / moon lighting variant — the light source changes, but contact shadow stays where surfaces meet

---

## 6. Light & the Hue-Shifted Ramp System

This section assumes familiarity with the MASTER_PALETTE document's ramp structure. Refer to MASTER_PALETTE.md for the full ramp definitions.

### 6.1 Core Principle

The hue-shifted ramp system means that **shadow colors are not simply darker versions of the midtone** — they shift in hue as well as value. This produces richer, more organic shading and is the key visual difference between AM Pixel's palette and a flat-shaded approach.

**General rule:**
- Moving toward **light** (highlight): shift hue slightly **warm** and **desaturate slightly**
- Moving toward **shadow**: shift hue slightly **cool** and **saturate slightly**

This is the fundamental opposite of what many artists expect. Shadows in ambient outdoor light are cooler and more saturated; highlights are warmer and paler.

### 6.2 Ramp Step Usage by Lighting Zone

| Zone on Form | Ramp Usage |
|---|---|
| Specular highlight (single pixel max) | Ramp step 1 (lightest) |
| Primary lit face | Ramp step 2 |
| Mid-tone (default/ambient face) | Ramp step 3 |
| Shadow face (form shadow) | Ramp step 4 |
| Deep shadow / contact shadow | Ramp step 5 (darkest) |

> 5-step ramps apply to hero and prominent NPC sprites. Small enemies and background characters may use 3-step ramps (light, mid, dark) to reduce visual complexity at small scales.

### 6.3 Environment Hue Shifts

When environment variants (Section 4) change the light's color temperature, the ramps themselves shift:

**Warm light (firelight, torchlight):**
- Lit faces: pull from warm ramp variants
- Shadow faces: use cool ramp variants as the complement
- The contrast between warm light and cool shadow intensifies the drama

**Cool light (moon, underwater, crystal):**
- Lit faces: pull from cool ramp variants
- Shadow faces: use warmer, slightly more saturated ramp variants
- This creates a "cold light / warm shadow" relationship consistent with outdoor night observation

**Diffuse light (overcast, underwater deep):**
- Reduce ramp range: use only steps 2–4 (skip the specular and deepest shadow)
- Shading still follows top-left convention but is compressed in contrast

### 6.4 Do Not Invent New Colors

Do not mix ramp colors to create new intermediate shades not present in MASTER_PALETTE. All shading transitions must use steps explicitly defined in the palette. If a transition feels too abrupt, the solution is dithering (see MASTER_PALETTE for dither rules) — not color invention.

---

## 7. Specular & Highlight Placement by Material

The specular highlight is the brightest single point on a lit surface — the direct reflection of the light source. In pixel art at small scales, this is **1–2 pixels maximum**. Placement and shape communicate material type.

### 7.1 Skin

- **Highlight position:** Upper-left of the forehead, upper-left of the nose bridge, upper-left of the cheekbone (for larger sprites)
- **Highlight character:** Soft — use ramp step 1 (lightest skin tone), but do not use pure white. Skin absorbs light; it does not create a mirror-bright reflection.
- **Size:** 1px at standard sprite scale; 2px for large sprites or battle sprites
- **Subsurface scatter implication:** The ear, nostril, and lip edges may use a slightly warm ramp step even on shadowed faces to suggest translucency. This is a 1px accent, not a shading rule.

### 7.2 Metal

- **Highlight position:** Most prominent upper-left point of the metal surface — for a breastplate, this is the top-left corner of the chest plate; for a sword blade, the left edge near the crossguard
- **Highlight character:** Sharp — use ramp step 1 (lightest) or pure white (palette's peak value) for polished metal. Metal reflects directly; the highlight is tight and bright.
- **Size:** 1px for small metal details; 1–3px for large armored surfaces (as a streak or point, never as a blob)
- **Secondary reflection:** Polished metal may show a faint secondary reflection on the opposite side from the highlight — this is 1px of ramp step 2, not a full highlight. Confirms that the surface is metallic without requiring pure white.
- **Matte/tarnished metal:** Reduce highlight intensity (ramp step 2 instead of 1, no pure white). The form shadow transition is the same; the specular peak is suppressed.

### 7.3 Cloth

- **Highlight position:** The peaks of folds — wherever the fabric bunches or drapes and presents its highest surface toward the light
- **Highlight character:** Broad and soft — cloth scatters light across a wider area. Use ramp step 2 across the lit fold peak, with step 1 only on the very tip of the highest fold.
- **Size:** Several pixels wide following the fold line, not a single point
- **Shadow in cloth:** The recesses between folds are the deepest shadow areas. Use ramp steps 4–5 in fold valleys.
- **Silk / satin cloth:** Shift toward metallic rules — tighter highlight, sharper specular. A silk robe's highlight is more like polished metal than rough linen.

### 7.4 Stone

- **Highlight position:** Upper-left face of raised stone surfaces (cobblestones, stone walls, castle blocks)
- **Highlight character:** Muted — stone is rough and does not produce a bright specular. Use ramp step 2 for the lit face; ramp step 1 only on sharp chiseled corners of cut stone.
- **Texture:** Stone surfaces use small-scale variation across the lit face (1px alternations between ramp step 2 and 3) to suggest rough texture. This variation is only visible on the lit face — the shadow face is a flatter ramp step 4–5.
- **Wet stone:** Increases specular intensity toward metal rules. A wet stone floor can use a 1px specular highlight (ramp step 1) at the point of wettest reflection.

### 7.5 Water Surfaces

- **Highlight position:** Upper-left of any water tile's surface; the pattern shifts with animation frames
- **Highlight character:** Sharp and moving — water reflects directly like metal, but the reflection breaks up across the animated surface
- **Implementation:** Water tile animation cycles through highlight positions to suggest movement. The brightest pixel (ramp step 1 / near-white) moves across the tile in the animation loop.
- **Deep water color:** The dark areas of water tiles use the palette's deepest cool shadow ramp, suggesting depth and opacity
- **Still water (puddles, mirrors):** Static highlight at the upper-left of the puddle's surface; the highlight is a fixed 1–2px rather than animated, matching the tile animation style of the surrounding area

---

## 8. Common Lighting Mistakes

These are the most frequently observed lighting errors in pixel art RPG production. Each has a specific cause and fix.

### 8.1 Double Light Sources

**What it looks like:** A sprite has highlights on both the upper-left *and* the upper-right of the same form. It appears to be lit from two directions simultaneously.

**Cause:** The artist drew a highlight on the "obvious" side of the form without checking consistency with the established source. Or, the artist copied a reference image that used a different lighting setup.

**Fix:** Before adding any highlight, identify the single light source for the current context (see Section 4). Every highlight on every pixel must be justified by that one source. If you're not sure where the highlight should land, ask: "Where would a lamp at the top-left cast the brightest light on this surface?" Place the highlight only there.

> **Rule:** One scene, one primary light source. Secondary fill is permitted but must never produce competing highlights.

### 8.2 Ambient Occlusion Inconsistency

**What it looks like:** Contact shadows appear under some objects on the ground but not others in the same scene. Or, the contact shadow is dramatically heavier on one sprite type than another without a visual logic reason.

**Cause:** Different artists applied their own occlusion intuition without referencing a standard. Some added strong contact shadows; others skipped them.

**Fix:** Follow the contact shadow rules in Section 5.3 uniformly. Every grounded object has the same weight of contact shadow unless a specific scene condition (floating spell effect, levitating enemy) explicitly overrides it. Establish a reference tile with the "correct" contact shadow and pin it visually for the team.

### 8.3 Highlight on the Wrong Face of a Form

**What it looks like:** A barrel or pillar has its highlight on the right side. A character's right shoulder is brighter than the left. The bottom of a hat brim is lit.

**Cause:** The artist may be self-lighting ("this side looks better bright") or copying a reference without translating the light direction.

**Fix:** For every convex form, the highlight belongs on the **upper-left arc** of that form. Test: mentally rotate the object so you can see all six faces — top, bottom, left, right, front, back. Light hits top and left. Shadow is on bottom and right. Translate that back to the sprite's ¾ or side view.

### 8.4 Over-Ambient Lighting

**What it looks like:** A character standing in a dark cave looks just as bright and fully-lit as they do in a sunny outdoor field.

**Cause:** The artist drew the sprite for the default outdoor lighting scenario and did not adjust the effective palette for the environment.

**Fix:** Review Section 4 for environment overrides. In dark cave areas away from torches, reduce the effective highlight — the mid-tone in the standard palette becomes the effective "lit" color, and ramp step 1 (the highlight) is suppressed or unused. The sprite appears in less light because it *is* in less light.

### 8.5 Pillow Shading

**What it looks like:** The darkest pixels are around the outline of the sprite, and the lightest pixels are in the center — a glowing, rounded, unrealistic look that does not follow any light source.

**Cause:** The artist instinctively placed shading at the sprite's edges "to give it depth," without thinking about a light direction.

**Fix:** Eliminate all pillow shading. Every dark pixel must be justified by the light source or by form shadow logic. The outline pixels are not automatically dark. The lightest pixels are on the upper-left face of each form, regardless of where that is relative to the sprite's outline.

---

## 9. Battle Background Lighting & Layer Depth

Battle backgrounds use parallax layering to create depth. Lighting is the primary tool for reinforcing that depth separation — not just parallax offset speed.

### 9.1 The Depth Lighting Principle

Objects closer to the viewer are **more affected by the primary light source** — they show fuller contrast, clearer highlights, and deeper shadows. Objects further away exhibit less contrast, are cooler (atmospheric haze shifts color toward cool and neutral), and their specular highlights are suppressed.

Apply this in layers:

| Layer | Distance | Contrast | Color Temperature | Highlight |
|---|---|---|---|---|
| Foreground elements | Closest | Full contrast (5 ramp steps) | Warm (default) | Full specular (ramp step 1) |
| Mid-ground architecture | Mid | Reduced contrast (3–4 ramp steps) | Slightly cooler | Muted highlight (ramp step 2) |
| Far background terrain | Far | Low contrast (2–3 ramp steps) | Cool, desaturated | No specular; only form light |
| Sky / atmosphere | Furthest | Flat or very subtle gradient | Color-defined (sunset, night) | Not applicable |

### 9.2 Light Direction in Battle Backgrounds

- The top-left light source applies to the foreground and mid-ground layers
- Far background layers are lit primarily from above (not directional left), since atmospheric perspective softens directionality
- Never introduce a conflicting light direction within the battle background — the enemy and hero sprites in front of the background must read as existing in the same light as the nearest parallax layer

### 9.3 Layer Separation Through Lighting Contrast

The contrast difference between layers is the key depth cue in a static or slow-parallax battle background:

- **Foreground:** High saturation, full ramp, visible specular
- **Mid-ground:** Reduce saturation by one perceptible step; suppress specular; use 3 ramp steps max
- **Far background:** Near-greyed, 2 ramp steps, haze shifts everything toward the sky color
- **Practical test:** Desaturate the battle background image entirely and look at it in greyscale. The foreground layer should be visibly higher in contrast than the background. If they're similar in greyscale contrast, the depth separation will feel flat.

### 9.4 Point Light Sources in Battle Backgrounds

Some battle environments include active light sources: torches on dungeon walls, glowing runes, fires. These affect the background layers but must not contradict the top-left source lighting on enemy/hero sprites.

- Point sources in battle backgrounds are **decorative** — they add color and atmosphere to the background layers only
- They do not relight the enemy or hero sprite
- If a fire source in the background would logically relight the scene, that is a design decision requiring a specific sprite variant — it is not solved by adjusting the background alone

---

## Revision Log

| Version | Date | Author | Change Summary |
|---|---|---|---|
| v1.0 | 2026-05-09 | AM Studio | Initial lock |

---

*AM Pixel Lighting Standard | Style Bible v1.0 | LOCKED*
