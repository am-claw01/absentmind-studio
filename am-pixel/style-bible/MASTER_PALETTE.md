# AM Pixel — Master Palette
**Style Bible | Phase 2 | LOCKED**

---

## Overview

This document defines the locked project-wide color palette for AM Pixel. Every ramp family is hue-shifted: **shadows pull cooler (toward blue-purple)**, and **highlights push warmer (toward yellow-orange or pink-cream)**, never simple brightness steps. All hex values are constrained to the **SNES 15-bit RGB color space** — each channel is a multiple of 8 (0–248).

**Reading a ramp entry:**
`[SHADE NAME] — #RRGGBB (R, G, B)`
Listed **highlight → base → shadow**, darkest last.

---

## 1. SKIN TONE RAMPS

### Usage Rules
- Use skin tone ramps exclusively for character flesh areas: face, hands, exposed limbs.
- Never mix ramps mid-character — pick one ramp per character and commit.
- Rim lighting on the lightest shade is permitted using Highlight Light neutrals (see §8).
- Shadow edges must use the deepest shade of the ramp; mid-tones fill the lit body planes.
- Avoid pure black outlines on skin; use the Deep Shadow shade for linework on skin areas instead.

---

### SKT-A · Warm Light Skin

> For fair to light-tan human characters.

| Shade | Hex | R, G, B |
|---|---|---|
| Highlight | `#F8E0B0` | 248, 224, 176 |
| Base | `#E8A870` | 232, 168, 112 |
| Mid-Shadow | `#C07848` | 192, 120, 72 |
| Deep Shadow | `#804858` | 128, 72, 88 |

**Hue Shift:** Highlight shifts warm yellow-cream (low blue saturation). Base is peachy-orange. Mid-Shadow desaturates and pulls toward rose-tan. Deep Shadow pivots to cool red-purple — blue channel rises relative to green, giving skin depth without muddiness.

---

### SKT-B · Warm Medium-Dark Skin

> For medium-brown to dark-brown human characters.

| Shade | Hex | R, G, B |
|---|---|---|
| Highlight | `#E8A858` | 232, 168, 88 |
| Base | `#C07838` | 192, 120, 56 |
| Mid-Shadow | `#885030` | 136, 80, 48 |
| Deep Shadow | `#503048` | 80, 48, 72 |

**Hue Shift:** Highlight is a warm golden-amber. Base reads as rich warm brown. Mid-Shadow pulls the orange warmth toward reddish-brown. Deep Shadow swings cool with elevated blue, landing in a purple-brown that reads as believable under-jaw and eye-socket darkness.

---

## 2. METAL RAMPS

### Usage Rules
- Use metal ramps for armor plates, weapons, buckles, and hard mechanical surfaces.
- Specular highlights (single-pixel or 2-pixel bright spots) should be pulled from the lightest shade.
- Dark rims and shadow undersides use the Deep Shadow shade.
- Never use metal ramps on leather or cloth surfaces; substitute Neutral Darks for straps.
- Iron/Steel is for utilitarian and military equipment; Gold/Brass for ornamental, royal, or ancient items.

---

### MTL-A · Iron / Steel

> Cold-worked metal, armor plating, sword blades.

| Shade | Hex | R, G, B |
|---|---|---|
| Highlight | `#E0E8F8` | 224, 232, 248 |
| Mid-Highlight | `#A0A8C0` | 160, 168, 192 |
| Base | `#686878` | 104, 104, 120 |
| Deep Shadow | `#303050` | 48, 48, 80 |

**Hue Shift:** Highlight leans icy blue-white (blue channel peaks). Mid-Highlight is a cool blue-grey. Base is a neutral steel grey with a slight blue lean. Deep Shadow shifts strongly into dark indigo-navy — the classic "cold metal" underside read.

---

### MTL-B · Gold / Brass

> Royal ornaments, coin trim, ancient relics, warm ceremonial metal.

| Shade | Hex | R, G, B |
|---|---|---|
| Highlight | `#F8F0A0` | 248, 240, 160 |
| Mid-Highlight | `#E8C040` | 232, 192, 64 |
| Base | `#C88820` | 200, 136, 32 |
| Deep Shadow | `#805018` | 128, 80, 24 |

**Hue Shift:** Highlight is pale warm lemon-yellow (maximum warmth). Mid-Highlight is saturated clean gold. Base deepens to rich amber-gold. Deep Shadow pulls toward warm reddish-brown — note that for warm hue families, "cooler" means toward orange-red rather than toward blue-purple, preserving a metallic identity while removing the yellow warmth. This keeps gold looking like aged, oxidized metal in shadows rather than turning green or grey.

---

## 3. CLOTH / FABRIC RAMPS

### Usage Rules
- Cloth ramps apply to tunics, capes, robes, dresses, pants, and all soft textile surfaces.
- Fold highlight placement: use lightest shade only on the fabric plane directly facing the light source.
- Use Deep Shadow in tight fold creases and fabric overlaps.
- Cloth ramps can be mixed on a single character (e.g., warm tunic + cool cape) but never blend ramps within a single fabric piece.
- Avoid using metal ramp shades for satin or silk — instead use Neutral Lights (§8) for the sheen pass.

---

### CLT-A · Warm Cloth — Crimson / Red

> Capes, tunics, adventurer's gear in warm red/scarlet palette.

| Shade | Hex | R, G, B |
|---|---|---|
| Highlight | `#F89080` | 248, 144, 128 |
| Base | `#D03030` | 208, 48, 48 |
| Mid-Shadow | `#800830` | 128, 8, 48 |
| Deep Shadow | `#480838` | 72, 8, 56 |

**Hue Shift:** Highlight shifts to warm salmon-orange (increased green channel gives orange warmth). Base is saturated mid-red. Mid-Shadow desaturates toward crimson-magenta with elevated blue. Deep Shadow lands in dark cool purple-red — the classic warm cloth shadow pivot.

---

### CLT-B · Cool Cloth — Sapphire / Blue

> Mage robes, noble garments, aquatic themes.

| Shade | Hex | R, G, B |
|---|---|---|
| Highlight | `#98C8F0` | 152, 200, 240 |
| Base | `#3878C8` | 56, 120, 200 |
| Mid-Shadow | `#184898` | 24, 72, 152 |
| Deep Shadow | `#102860` | 16, 40, 96 |

**Hue Shift:** Highlight shifts toward icy sky-blue with reduced saturation and warm cream undertone (high G and B). Base is a vivid mid-blue. Mid-Shadow deepens to royal blue. Deep Shadow becomes dense navy-indigo — shadows cool into purple-blue territory as the hue rotates slightly toward violet.

---

### CLT-C · Neutral Cloth — Sand / Linen

> Common folk garments, undershirts, sacks, bandages, worn fabric.

| Shade | Hex | R, G, B |
|---|---|---|
| Highlight | `#E8E0D0` | 232, 224, 208 |
| Base | `#A09080` | 160, 144, 128 |
| Mid-Shadow | `#685860` | 104, 88, 96 |
| Deep Shadow | `#403040` | 64, 48, 64 |

**Hue Shift:** Highlight is warm cream-linen (slight yellow warmth, high R and G relative to B). Base is a warm grey-tan. Mid-Shadow shifts the hue into cool grey-mauve (blue channel rises relative to green-red). Deep Shadow is a cool desaturated purple-grey — the "old linen in shadow" read.

---

## 4. NATURE RAMPS

### Usage Rules
- Nature ramps apply to all environmental and organic world elements.
- Do not use nature ramps on characters unless for fur, feathers, or scales on non-human creatures.
- Foliage ramps handle all plant matter; use darker shades at canopy overlaps and lighter shades on sun-facing leaf clusters.
- Earth ramps handle soil, mud, dirt paths, and dry desert ground.
- For mixed terrain (e.g., mossy stone), layer Stone ramps over Earth ramps on separate tiles.

---

### NAT-A · Foliage — Forest Green

> Leaves, grass, bushes, vines, plant life.

| Shade | Hex | R, G, B |
|---|---|---|
| Highlight | `#B0E848` | 176, 232, 72 |
| Base | `#58A818` | 88, 168, 24 |
| Mid-Shadow | `#286808` | 40, 104, 8 |
| Deep Shadow | `#183840` | 24, 56, 64 |

**Hue Shift:** Highlight is warm yellow-green (high green + elevated red, low blue) — sunlit leaf tips. Base is a saturated mid-green. Mid-Shadow cools to deeper forest green. Deep Shadow pivots strongly toward teal-black with rising blue channel — deep forest canopy shadow reads as cool and atmospheric.

---

### NAT-B · Earth — Soil / Terrain

> Dirt paths, soil tiles, dry earth, mud banks.

| Shade | Hex | R, G, B |
|---|---|---|
| Highlight | `#E8C880` | 232, 200, 128 |
| Base | `#B07840` | 176, 120, 64 |
| Mid-Shadow | `#704828` | 112, 72, 40 |
| Deep Shadow | `#402838` | 64, 40, 56 |

**Hue Shift:** Highlight is warm sandy yellow-cream. Base is a medium warm brown. Mid-Shadow pulls toward reddish-ochre. Deep Shadow shifts to cool purple-brown — underground and deep-crack soil reads as desaturated with blue-purple cold.

---

## 5. STONE RAMP

### Usage Rules
- Use for dungeon walls, castle masonry, cliff faces, cobblestones, and ruins.
- Stone ramps should combine with neutral darks in mortar lines and cracks.
- Avoid using foliage or wood ramps directly alongside stone without a transition pixel row.
- Wet stone effect: add a single pixel of MTL-A Mid-Highlight along top edge of stone blocks.

---

### STN-A · Dressed Stone / Grey Masonry

> Castle walls, dungeon tile, cobble, cliff face.

| Shade | Hex | R, G, B |
|---|---|---|
| Highlight | `#D0D0C8` | 208, 208, 200 |
| Base | `#888880` | 136, 136, 128 |
| Mid-Shadow | `#505058` | 80, 80, 88 |
| Deep Shadow | `#282840` | 40, 40, 64 |

**Hue Shift:** Highlight is a warm pale grey (very slight yellow bias — R=G > B). Base is an even neutral grey with micro warmth. Mid-Shadow shifts the grey toward cool blue-grey (blue channel rises above red and green). Deep Shadow becomes dark indigo-grey — cracks and cavity shadows have a distinctly cool, underground atmospheric quality.

---

## 6. WOOD RAMP

### Usage Rules
- Use for wooden floors, doors, chests, furniture, shields, staves, and ship planking.
- Wood grain detail lines: use Deep Shadow shade as a 1px line on Base.
- Weathered/aged wood: desaturate one step by mixing Wood Base with Neutral Darks Mid (§7).
- Do not use Wood ramps for flesh tones — the hue range overlaps dangerously with SKT-B.

---

### WOD-A · Warm Wood — Pine / Oak

> Standard timber, treasure chests, wooden buildings.

| Shade | Hex | R, G, B |
|---|---|---|
| Highlight | `#F0C878` | 240, 200, 120 |
| Base | `#A06028` | 160, 96, 40 |
| Mid-Shadow | `#604018` | 96, 64, 24 |
| Deep Shadow | `#382028` | 56, 32, 40 |

**Hue Shift:** Highlight is a warm golden-tan (yellow bias, elevated R and G). Base is a classic medium warm brown. Mid-Shadow pulls toward reddish-dark brown. Deep Shadow pivots to cool purple-brown — deep knotholes and shadow undersides take on a dark, slightly cold character that reads as depth without looking like black.

---

## 7. MAGIC / ARCANE RAMP

### Usage Rules
- Use exclusively for magical effects, arcane energy, spell particles, enchanted items glowing rims, and magical UI elements.
- Never use this ramp for fabric or skin — it will read as unnatural (which is fine for pure magic objects, not for character design).
- Aura effects: use Highlight as a 1-pixel rim glow on otherwise-normal palette areas.
- The magic ramp can be applied sparingly to eyes of magical entities.
- For fire-based magic, use CLT-A (Warm Cloth — Crimson) shadows + Magic Highlight as the flame tip.

---

### MGC-A · Arcane Violet / Spirit Purple

> Magic auras, spell effects, enchanted runes, elemental energy.

| Shade | Hex | R, G, B |
|---|---|---|
| Highlight | `#F0C0F8` | 240, 192, 248 |
| Base | `#9828D8` | 152, 40, 216 |
| Mid-Shadow | `#500890` | 80, 8, 144 |
| Deep Shadow | `#200858` | 32, 8, 88 |

**Hue Shift:** Highlight is a warm pink-lavender (warm pink bias from elevated R and B with high brightness) — the outer bloom of magic light is slightly warm. Base is a highly saturated vivid violet. Mid-Shadow deepens to indigo with heavy blue dominance. Deep Shadow is a rich dark violet-navy — the core or root of a magical effect, densest color in the ramp, used at the energy source.

---

## 8. NEUTRAL RAMPS

### Usage Rules
- Neutral ramps are the spine of the entire palette — they serve as universal outline, transition, shadow fill, and interface colors.
- **Neutral Darks** handle outlines, cast shadows, dark UI panels, and dungeon atmosphere fills.
- **Neutral Lights** handle rim lighting, fog, sky fades, paper/scroll backgrounds, and interface highlights.
- Do not use pure `#000000` black in any sprite outline — use NDK-1 (Deep Cold Black) instead.
- Do not use pure `#FFFFFF` white for any highlight — use NLT-5 (Cool Blue-White) instead.

---

### NDK · Neutral Darks — Shadow Family

> Universal outlines, cast shadows, dark backgrounds, depth fills.

| Shade | Name | Hex | R, G, B |
|---|---|---|---|
| NDK-1 | Deep Cold Black | `#181020` | 24, 16, 32 |
| NDK-2 | Dark Indigo Shadow | `#302840` | 48, 40, 64 |
| NDK-3 | Mid-Dark Cool Purple | `#483858` | 72, 56, 88 |
| NDK-4 | Warm Dark (Transition) | `#604858` | 96, 72, 88 |
| NDK-5 | Purple-Tinged Shadow | `#785870` | 120, 88, 112 |

**Hue Shift:** NDK-1 is the darkest possible — near-black but with a cool blue-purple bias so it never looks flat. The scale warms very slightly as it rises (NDK-4/5 have elevated R relative to pure cool) to serve as a bridging shadow tone when transitioning from cool shadows into mid-tones.

---

### NLT · Neutral Lights — Highlight Family

> Rim lighting, sky tints, paper/parchment BG, interface shine, fog.

| Shade | Name | Hex | R, G, B |
|---|---|---|---|
| NLT-1 | Warm Cream White | `#F8F0E0` | 248, 240, 224 |
| NLT-2 | Warm Off-White | `#E8D8C8` | 232, 216, 200 |
| NLT-3 | Warm Light Grey | `#D0C8B8` | 208, 200, 184 |
| NLT-4 | Cool Light Grey | `#C0C8D8` | 192, 200, 216 |
| NLT-5 | Cool Blue-White | `#D0D8F0` | 208, 216, 240 |

**Hue Shift:** NLT-1 is warm cream (high R, mid G, lower B) — the warmth of direct sunlight or torch glow. The scale transitions through neutral light greys and crosses into cool territory at NLT-4/5, which carry the cool rim-light and ambient sky-light tones. This allows a character to have a warm key light on one side and a cool fill light on the other using just this one ramp.

---

## Palette Summary Table

| Family | Code | Hex Values (H → Base → S) |
|---|---|---|
| Skin Warm Light | SKT-A | `#F8E0B0` `#E8A870` `#C07848` `#804858` |
| Skin Warm Med-Dark | SKT-B | `#E8A858` `#C07838` `#885030` `#503048` |
| Iron / Steel | MTL-A | `#E0E8F8` `#A0A8C0` `#686878` `#303050` |
| Gold / Brass | MTL-B | `#F8F0A0` `#E8C040` `#C88820` `#805018` |
| Cloth Warm Red | CLT-A | `#F89080` `#D03030` `#800830` `#480838` |
| Cloth Cool Blue | CLT-B | `#98C8F0` `#3878C8` `#184898` `#102860` |
| Cloth Neutral Linen | CLT-C | `#E8E0D0` `#A09080` `#685860` `#403040` |
| Foliage Green | NAT-A | `#B0E848` `#58A818` `#286808` `#183840` |
| Earth Brown | NAT-B | `#E8C880` `#B07840` `#704828` `#402838` |
| Dressed Stone | STN-A | `#D0D0C8` `#888880` `#505058` `#282840` |
| Warm Wood | WOD-A | `#F0C878` `#A06028` `#604018` `#382028` |
| Arcane Magic | MGC-A | `#F0C0F8` `#9828D8` `#500890` `#200858` |
| Neutral Darks | NDK | `#181020` `#302840` `#483858` `#604858` `#785870` |
| Neutral Lights | NLT | `#F8F0E0` `#E8D8C8` `#D0C8B8` `#C0C8D8` `#D0D8F0` |

---

## Cross-Ramp Compatibility Notes

- **SKT-A/B + NDK-1:** Outline skin areas with NDK-1, never MTL-A or Stone shades.
- **MTL-A + NDK-2/3:** Steel armor shadow fills blend naturally with NDK-2 and NDK-3 for chainmail depth.
- **NAT-A + STN-A:** Mossy stone transitions work by placing NAT-A Base pixels dotted over STN-A Mid-Shadow.
- **CLT-A + MGC-A:** Enchanted red fabric uses CLT-A ramp for the cloth body and MGC-A Highlight as a 1-pixel rim edge glow.
- **NLT-5 + MTL-A Highlight:** These two shades are intentionally close — NLT-5 (`#D0D8F0`) can substitute as a soft secondary metal highlight where maximum brightness would be garish.

---

*AM Pixel Master Palette | Style Bible v1.0 | LOCKED*
