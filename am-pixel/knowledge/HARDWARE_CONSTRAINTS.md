# AM Pixel — Hardware Constraints
**Knowledge Base | Phase 1 Boot Training**

This document covers the technical constraints of six retro gaming platforms. These constraints define the aesthetic vocabulary AM Pixel must learn — not as hard limits to enforce by default, but as the craft context that shaped the pixel art traditions we are studying.

---

## Platform 1 — Super Nintendo Entertainment System (SNES)

**Primary reference platform for AM Pixel.**

### Display
- Resolution: 256×224 (standard), 512×224 (hi-res mode), 256×239 (PAL)
- Color depth: 15-bit RGB (5 bits per channel), ~32,768 possible colors
- Colors on screen simultaneously: up to 256 (from 32,768 palette)
- Background layers: up to 4 simultaneous BG layers (Mode 0–7)

### Sprites
- Sprite sizes: 8×8, 16×16, 32×32, 64×64 pixels (configurable per object layer)
- Max sprites on screen: 128
- Max sprites per scanline: 32 (flicker occurs above this)
- Colors per sprite palette: 15 + 1 transparent (16 slots, one reserved)
- Sprite palettes: 8 palettes available for sprites (OBJ palettes)
- Max colors per individual sprite: 15 (one transparency slot)

### Tiles
- Tile size: 8×8 pixels (fundamental unit)
- Characters (tiles) in VRAM: 1024 (8×8) or 512 (16×16)
- Tile map size: 32×32 or 64×64 tiles

### Rendering
- No hardware anti-aliasing or alpha blending (Mode 7 has scaling/rotation)
- Mode 7: single affine-transformed background layer (used for pseudo-3D)
- Color math: additive/subtractive blending between layers (limited)
- No true transparency — one color per palette is transparent

### Craft implications
- Pixel artists worked with exactly 15 colors + transparent per character
- Outline technique critical: must be darkened local color, not pure black (wastes a palette slot and looks flat)
- Hue-shifted color ramps essential: brightness + hue shift for depth illusion
- Every pixel deliberate — no sub-pixel rendering, no gradients
- Shading with 2–3 shades per region (more = palette exhaustion)

---

## Platform 2 — Nintendo Entertainment System (NES)

### Display
- Resolution: 256×240 (NTSC), 256×239 displayed (overscan)
- Color depth: Fixed hardware palette of 54 colors (not user-defined)
- Colors on screen: Up to 25 simultaneous (4 palettes × 4 colors, minus shared background)

### Sprites
- Sprite sizes: 8×8 or 8×16 pixels only
- Max sprites on screen: 64
- Max sprites per scanline: 8 (heavy flicker above this — used intentionally by some games)
- Colors per sprite: 3 + transparent (4 slots, 1 reserved)
- Sprite palettes: 4 palettes for sprites

### Craft implications
- Extreme color scarcity: 3 colors + transparent per sprite — every color choice critical
- Flicker used intentionally for overlapping sprites
- Dithering common to simulate additional colors/gradients
- Character read must work at 8×8 scale — silhouette is everything
- No sub-pixel detail possible at this resolution

---

## Platform 3 — Sega Genesis / Mega Drive

### Display
- Resolution: 320×224 or 256×224 (320 mode preferred for most games)
- Color depth: 9-bit RGB (3 bits per channel), 512 possible colors
- Colors on screen: 64 simultaneously (4 palettes × 16 colors)

### Sprites
- Sprite sizes: 8×8, 16×16, 24×24, 32×32 (in 8-pixel increments)
- Max sprites on screen: 80
- Max sprites per scanline: 20 (320 mode) or 16 (256 mode)
- Colors per sprite palette: 16 (including 1 transparent)
- Sprite palettes: 4 (shared between sprites and backgrounds)

### Craft implications
- 512-color palette gives slightly more flexibility than SNES's 32,768 but fewer on-screen
- 9-bit color means more limited tonal range — requires stronger hue shifts
- Sonic-era aesthetic: strong silhouettes, bold primary colors, high contrast
- Outline on dark backgrounds more common than SNES due to limited palette depth

---

## Platform 4 — Game Boy (Original / Color)

### Original Game Boy
- Resolution: 160×144
- Color depth: 4 shades of green (not RGB)
- Colors: 4 shades total (white, light gray, dark gray, black — in greenish tint)
- Sprites: 8×8 or 8×16, max 40 on screen, 10 per scanline
- Colors per sprite: 3 + transparent

### Game Boy Color
- Resolution: 160×144
- Color depth: 15-bit RGB (same as SNES) — 32,768 possible
- Colors on screen: 56 simultaneous
- Sprites: 8×8 or 8×16, max 40 on screen
- Colors per sprite palette: 4 (3 + transparent)

### Craft implications
- Original GB demands pure value-based composition — no hue, only luminance
- 4-shade constraint teaches fundamental form reading through value alone
- GBC: extreme color economy (4 colors per sprite) but with hue freedom
- Tiny canvas (160×144) demands maximum silhouette clarity
- Dithering used extensively on both variants to suggest additional tones

---

## Platform 5 — PlayStation 1 (PS1)

### Display
- Resolution: 256×240, 320×240, 512×240, 640×480 (various modes)
- Color depth: 24-bit RGB full color (16.7 million colors)
- Colors on screen: unlimited (hardware renders true color)

### Sprites / 2D
- Tile-based 2D: 16×16 tiles standard
- Texture pages: 256×256 pixel texture memory regions
- 2D sprites: rendered as textured polygons
- Color modes: 4-bit (16 colors), 8-bit (256 colors), 15-bit (32,768 colors) per texture

### Craft implications
- Transition era: pixel art coexisted with early 3D
- 2D PS1 games (Castlevania: Symphony, Final Fantasy Tactics) show mature pixel art with richer palettes
- Texture warping and affine texture distortion artifacts are characteristic of the era
- 8-bit texture mode (256 colors) most common for 2D sprite work
- Artists had more color freedom but still made deliberate palette choices for cohesion

---

## Platform 6 — Game Boy Advance (GBA)

### Display
- Resolution: 240×160
- Color depth: 15-bit RGB, 32,768 colors
- Colors on screen: up to 256 simultaneous (bitmap modes) or 512 (tiled modes with 2 palettes)

### Sprites
- Sprite sizes: 8×8 to 64×64 (multiple sizes available)
- Max sprites on screen: 128
- Colors per sprite: 16 (4-bit mode) or 256 (8-bit mode)
- Sprite palettes: 16 palettes of 16 colors (4-bit) or 1 palette of 256 colors (8-bit)

### Craft implications
- Closest portable hardware to SNES in terms of color capability
- Stronger ambient light compensation needed (no backlight on original GBA) — artists used higher contrast and saturation
- Final Fantasy VI GBA port famously over-saturated for this reason
- Larger sprite sizes available than GBA predecessors
- Rich tileset and sprite work achievable — many SNES ports ran on GBA

---

## Cross-Platform Craft Principles

These constraints shaped universal pixel art craft principles:

1. **Silhouette first** — every platform limits color; the shape must read before any color is perceived
2. **Palette economy** — every color slot has a cost; unused colors are wasted design space
3. **Hue-shifted ramps** — pure brightness shifts look flat; hue rotation toward warm highlights and cool shadows creates depth illusion within tiny palettes
4. **No anti-aliasing** — sub-pixel blending was not available; smooth curves are implied by pixel placement, not softened
5. **Outline as information** — outlines separate character from background and internally separate regions; pure black outlines waste a palette slot
6. **3-shade maximum per region** — base + shadow + highlight per region; more = palette exhaustion without proportional quality gain
7. **Dithering as texture** — checkerboard patterns between two colors simulate a third tone; overuse creates noise

---

*AM Pixel Hardware Constraints | Phase 1 Boot Training | v1.0*
