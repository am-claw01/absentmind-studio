# AM Pixel — Mistake Taxonomy
**Knowledge Base | Phase 1 Boot Training**

---

## Overview

This taxonomy catalogs recurring failure modes in pixel art production, organized by skill tier. Each entry is structured for both human diagnosis and automated detection — entries are cross-referenced to tooling in `rubric_scorer.py`, `banding_detector.py`, `outline_checker.py`, `palette_auditor.py`, `animation_linter.py`, and related scripts. Severity ratings run from **Low** (minor polish issue) to **Critical** (asset is unusable or style-breaking).

Use this document to:
- Train the AM Pixel rubric scorer on what to flag and why
- Give artists corrective principles, not just error messages
- Build a shared vocabulary for critique and iteration

---

## Tier 1 — Beginner Failures

*These are the most common mistakes made by artists new to pixel art. They stem from misapplied habits from other mediums (painting, vector, digital illustration) and from misunderstanding pixel art's core constraint: every pixel is intentional.*

---

### B-01 · Pillow Shading

**Description:**
Shading is applied by outlining the interior of a shape with progressively darker rings, like contour lines on a topographic map. The result reads as a flat, inflated, "pillow-like" surface with no coherent light direction.

**Visual Symptoms:**
- Shading rings that perfectly mirror the silhouette, inset by 1–2 pixels
- No highlights or shadows that imply a light source angle
- Surfaces look rounded/puffy regardless of their intended 3D form
- Gradient appears symmetrical on all sides of a shape

**Root Cause:**
The artist is shading by outline proximity rather than by understanding the geometry of the surface and its relationship to a light source. It is the easiest shading pattern to apply mechanically, so it becomes a crutch. Often imported from raster painting habits where soft brushes produce a similar effect automatically.

**Corrective Principle:**
Define a single light source before placing any shading. Every shadow and highlight placement must be answerable to the question: "Where is the light coming from?" Cluster highlights toward the light-facing surface. Shadows fall on the side opposite the light. The silhouette edge should not uniformly darken.

**Automated Detection Hook:**
`rubric_scorer.py` — shading ring detector; checks if darkened pixel bands trace the silhouette at uniform inset offsets. Flag assets where shading gradient correlation to silhouette distance exceeds threshold.

**Severity:** 🔴 High — Immediately visible, breaks form, indicates foundational shading misunderstanding.

---

### B-02 · Pure Black Outlines

**Description:**
All outline pixels are set to pure black (`#000000` or closest palette equivalent) regardless of context, background color, or the color of the form being outlined.

**Visual Symptoms:**
- Uniform black border around all sprites, regardless of form color
- Figures look stamped or pasted onto backgrounds rather than integrated
- Outlines disappear or look harsh against dark backgrounds
- No sense of atmosphere, depth, or subsurface edge variation

**Root Cause:**
Pure black is the default choice when no thought is given to outline color. It is the "safe" option because it always provides contrast, but it ignores how outlines interact with lighting, background, and form identity. Often a direct carry-over from non-pixel illustration or line art habits.

**Corrective Principle:**
Outline pixels should be a dark, saturated hue related to the form color — not neutral black. For a red character, outlines should be dark crimson. Outlines facing a light source can be lightened ("selective outlining"). On dark backgrounds, outlines may be partially removed. Use `#000000` sparingly, if at all.

**Automated Detection Hook:**
`outline_checker.py` — scans border pixels of sprite silhouettes and flags any pixel at or below `rgb(10, 10, 10)` as a pure-black violation. Reports percentage of outline pixels that are pure black.

**Severity:** 🟠 Medium-High — Style-breaking, signals beginner level, degrades integration.

---

### B-03 · Anti-Aliasing (AA) Misuse

**Description:**
Anti-aliasing pixels — intermediate colors placed at diagonal edges to smooth the staircase effect — are either entirely absent (making all diagonals jagged), applied incorrectly (wrong color, wrong placement), or applied where they should not be (internal details, flat edges, tiny sprites).

**Visual Symptoms:**
- Harsh staircase jaggies on all diagonal curves
- OR: blurry, smudged edges from over-applied AA
- AA pixels that use the wrong intermediate hue (grey AA on a colored form)
- AA applied to 8×8 or 16×16 sprites where it reads as noise

**Root Cause:**
AA is borrowed from raster graphics without understanding that in pixel art it is a deliberate manual tool, not an automatic filter. Artists either forget it exists, apply it via software anti-alias filters (which use wrong colors), or apply it at scales where individual pixels are too large to blend visually.

**Corrective Principle:**
Manual AA is only meaningful at display scales ≥2×. The AA pixel should be a color exactly between the outline and the background in both hue and value. Apply only to curves and long diagonals. Never use software-generated AA. On small sprites (≤16px), AA often makes things worse — omit it.

**Automated Detection Hook:**
`outline_checker.py` — detects diagonal edge pixels with no intermediate color neighbors (missing AA), and flags intermediate pixels that don't fall within the expected hue/value range of their two adjacent regions (wrong-color AA).

**Severity:** 🟡 Medium — Highly context-dependent. AA absence on large sprites is high severity; AA presence on small sprites may itself be the error.

---

### B-04 · Orphan Pixels

**Description:**
Single isolated pixels appear disconnected from any nearby form, either as stray marks in open space or as lone pixels jutting from a silhouette with no connection to the intended shape.

**Visual Symptoms:**
- Single-pixel dots in empty areas of a sprite
- One-pixel protrusions off a silhouette that serve no readable shape purpose
- Diagonal corners of pixel clusters that visually detach from the main mass
- "Salt and pepper" noise scattered across flat color regions

**Root Cause:**
Orphan pixels are usually accidents — stray clicks during editing — or the unexamined result of a tool operation (bucket fill leaving single-pixel gaps, selection edge artifacts). Sometimes they come from attempting a detail too small to render at the current resolution.

**Corrective Principle:**
Every pixel must belong to a readable group. If a pixel cannot be visually "read" as part of a larger shape or detail, it is an orphan and should be removed. At 1× zoom, regularly zoom to 1× to spot orphans that only appear as errors at actual size. Use connectivity analysis: if a pixel has zero same-color neighbors within 1px, it is a candidate for removal.

**Automated Detection Hook:**
`rubric_scorer.py` — isolated pixel detector; flags any non-background pixel with zero 4-directionally connected neighbors of similar color. Reports orphan pixel count and coordinates.

**Severity:** 🟡 Medium — Appears as noise/error, breaks polish, but is easy to fix.

---

### B-05 · Proportion Errors

**Description:**
The relative sizes of body parts, objects, or architectural elements are inconsistent with the intended anatomy or design — heads too large or small relative to body, limbs mismatched, objects that change apparent scale between frames.

**Visual Symptoms:**
- Characters with visibly wrong head-to-body ratios (not stylized — unintentional)
- One arm rendered larger than the other with no perspective justification
- Objects in a scene at incompatible scales (a chair larger than a door)
- Inconsistent character height across frames of the same animation

**Root Cause:**
At small resolutions, pixel-rounding errors accumulate. An arm intended to be half the body width may end up one pixel off, which at 16px = 6% error visible to the eye. Artists also work zoomed in and lose the gestalt view, fixing local details while the overall proportion drifts.

**Corrective Principle:**
Define a pixel grid spec before drawing: head height in pixels, body height, limb widths. Work with a reference silhouette layer. Zoom to 1× frequently. For characters, use a consistent "cap height" unit — e.g., head = 4px tall, body = 12px. All proportions derive from that unit.

**Automated Detection Hook:**
`rubric_scorer.py` — cross-frame proportion checker; measures bounding box of detected body regions across animation frames and flags frames where proportions deviate >10% from the established frame-0 baseline.

**Severity:** 🟠 Medium-High — Breaks character consistency; critical for animation assets.

---

### B-06 · Readability Failures

**Description:**
The sprite's primary read — what it IS at a glance — is unclear. The silhouette does not communicate the subject, key details are lost at display size, or the color scheme fails to separate figure from ground.

**Visual Symptoms:**
- Sprite is unidentifiable at 1× zoom without zooming in
- Figure blends into background due to similar value/hue
- Important features (face, weapon, interaction point) are visually buried
- Silhouette reads as a blob rather than a recognizable form

**Root Cause:**
Artists focus on internal detail (texture, shading complexity) before establishing a readable silhouette and value structure. The silhouette is the first layer of communication in pixel art — if it fails, all internal detail is wasted.

**Corrective Principle:**
Design and test the silhouette first in flat color. If it's unreadable as a solid shape, no amount of internal detail will fix it. Ensure the primary read (what is it?) is clear at 1× zoom. Use strong value contrast between figure and ground. Limit detail to what survives at display resolution.

**Automated Detection Hook:**
`rubric_scorer.py` — silhouette clarity check; converts sprite to 1-bit silhouette and measures convexity ratio and perimeter complexity. Extremely irregular or blob-like silhouettes trigger a readability warning. Also cross-references sprite against background palette for contrast ratio.

**Severity:** 🔴 High — The most fundamental failure; the sprite does not function at its intended use.

---

## Tier 2 — Intermediate Failures

*These failures appear once the artist has overcome beginner habits but is now navigating more nuanced decisions about color, consistency, and craft. They require understanding pixel art theory, not just technique.*

---

### I-01 · Color Banding

**Description:**
Shading transitions use bands of flat color that are too uniform in width and too evenly spaced, creating a striped, mechanical look rather than a natural form. Each shade appears as a distinct stripe rather than part of a continuous surface.

**Visual Symptoms:**
- Shading bands of equal or near-equal pixel width running parallel across a form
- Distinct, hard-edged "steps" between shades with no shape variation
- The shaded area looks like a bar chart laid over the sprite
- No use of dithering, tapering, or irregular band boundaries to suggest volume

**Root Cause:**
The artist understands that multiple shades are needed but applies them mechanically — "1 pixel of shade A, 1 pixel of shade B" — without considering how light wraps around the actual 3D geometry of the form. Banding treats shading as a 2D striping problem rather than a volumetric one.

**Corrective Principle:**
Shade bands should vary in width according to curvature. On a sphere, the midtone band is widest at the equator; the bright and dark bands taper toward the poles. Use irregular band edges — jagged, interlocking, or dithered transitions — to imply surface complexity. Wider forms need more gradual transitions; narrow forms may need only 2 shades.

**Automated Detection Hook:**
`banding_detector.py` — primary tool; runs horizontal/vertical scan lines across shading regions and measures the regularity of shade band widths. Flags assets where band width variance falls below threshold (too uniform = banding). Also measures band edge straightness.

**Severity:** 🟠 Medium-High — Common, immediately recognizable, degrades perceived skill level significantly.

---

### I-02 · Incorrect Dithering

**Description:**
Dithering — the use of alternating pixels from two colors to simulate a third intermediate tone — is applied in the wrong context, with the wrong pattern, or at the wrong scale, producing noise or visual confusion rather than a smooth gradient.

**Visual Symptoms:**
- Checkerboard dither patterns visible at display resolution (too large to blend)
- Dithering applied to flat color areas that should be solid
- Wrong colors used in dither (colors not adjacent in the palette ramp)
- Dithering on 8×8 or 16×16 sprites where single pixels are too prominent
- Dither pattern inconsistent with the light direction or surface contour

**Root Cause:**
Dithering is misunderstood as a general "detail" technique rather than a perceptual blending tool. It only works when pixels are small enough to blend at viewing distance. Artists apply it because it "looks complex" without understanding the optical blending requirement or the palette relationship between the dithered colors.

**Corrective Principle:**
Only dither between adjacent steps on the same palette ramp. The two dithered colors should be one step apart in value. Dithering should follow the form's contour, not be applied in flat grid patterns. At small sprite sizes (≤32px), use dithering only for gradients that span ≥4 pixels. Consider the display scale: at 2× zoom, a checkerboard dither blends; at 1× zoom on a small sprite, it may not.

**Automated Detection Hook:**
`banding_detector.py` — dither pattern analyzer; detects checkerboard alternation patterns and checks whether the two alternating colors are adjacent in the registered palette ramp. Flags dithers using non-adjacent palette colors. Also reports dither region size vs. sprite size ratio.

**Severity:** 🟡 Medium — Incorrect dithering looks worse than no dithering; degrades quality but does not break function.

---

### I-03 · Palette Bloat

**Description:**
The sprite uses far more unique colors than are necessary for its visual complexity — often 30–60+ colors on assets that should use 6–16. Extra colors appear as slight variations of existing palette entries, near-duplicates, or one-off colors used on single pixels.

**Visual Symptoms:**
- Eyedropper on adjacent pixels returns slightly different hex values
- Color picker shows dozens of near-identical swatches
- No clear palette ramp structure; colors feel arbitrary
- Asset fails to conform to any defined palette system

**Root Cause:**
Artists use soft brushes, airbrushes, or gradient tools that generate continuous color ranges instead of selecting from a fixed palette. Importing from non-pixel-art source images also introduces thousands of colors. Without a strict palette lock, every anti-alias, edge softening, or blend operation adds new unique colors.

**Corrective Principle:**
Define the sprite's palette before drawing: how many ramps, how many steps per ramp. For a typical character sprite, 3–4 ramps of 3–4 steps each = 9–16 colors maximum. After completion, run a palette reduction pass. Every color in the sprite must be intentional and part of a defined ramp. Index the image and use only indexed colors.

**Automated Detection Hook:**
`palette_auditor.py` — primary tool; counts unique colors, identifies near-duplicate colors within a configurable delta-E threshold, reports ramp structure (or lack thereof), and flags sprites exceeding the project's maximum palette size. Outputs a palette visualization.

**Severity:** 🟠 Medium-High — Bloated palettes break style consistency, prevent palette-swap features, and indicate uncontrolled workflow.

---

### I-04 · Inconsistent Light Source

**Description:**
The light source direction changes between shading regions of the same sprite, between frames of an animation, or between sprites that share a scene. Highlights appear on opposite sides of different elements within the same asset.

**Visual Symptoms:**
- Character's torso lit from the left, head lit from the right
- Shadow falls differently on each limb with no environmental justification
- Highlights shift position between animation frames on a non-moving surface
- Different sprites in a tileset shaded from inconsistent angles

**Root Cause:**
The artist shades each region independently without committing to a global light source. When working zoomed in on individual parts, it is easy to shade the "locally correct" looking version of each piece without checking them against each other. In animation, new frames are often shaded without referencing the lighting of established frames.

**Corrective Principle:**
Establish light source direction as a project constant — for AM Pixel, document it in the sprite's spec sheet. Before shading, mark the light angle on every major surface. In animation, the light source does not move unless the environment changes. Create a "lighting reference frame" and check all subsequent frames against it. Use a master light spec in the project style guide.

**Automated Detection Hook:**
`rubric_scorer.py` — light consistency analyzer; detects the centroid of the brightest pixels in each detected body region and checks whether all centroids fall within the expected angular range of the declared light source. Cross-frame comparison flags centroid drift on static surfaces.

**Severity:** 🔴 High — Destroys the sense of a shared 3D space; makes the sprite feel incoherent even if individual regions look polished.

---

### I-05 · Texture Noise

**Description:**
Surface texture is rendered as random or semi-random pixel variation rather than as a structured, readable pattern. The result looks like static or grain rather than an identifiable material (stone, wood, fabric, metal).

**Visual Symptoms:**
- Scattered light/dark pixels across a surface with no directional or structural pattern
- Texture that reads as "noise" at 1× but resolves into something at 8× zoom
- No repetition, rhythm, or motif — texture feels random
- Texture that visually competes with the form's shading instead of reinforcing it

**Root Cause:**
Artists understand that "texture = variation" but don't understand that pixel art texture must be *structured* variation — a defined motif repeated with controlled irregularity. Without this structure, even small amounts of variation become noise. Also caused by using photographic textures as reference at scales where individual pixels don't correspond to material microstructure.

**Corrective Principle:**
Design texture as a motif first: what is the repeating unit of this material? For stone: irregular polygon outlines. For wood: directional grain lines. For fabric: diagonal weave pattern. Place the motif deliberately, then vary it with constraint. Texture should reinforce the form — it should be denser/higher contrast in shadows, lighter/sparser in highlights. Never randomize — always decide.

**Automated Detection Hook:**
`rubric_scorer.py` — texture structure analyzer; applies entropy measure to non-edge interior regions. High entropy with low spatial autocorrelation = noise. Also checks whether pixel variation within interior regions follows a directional pattern consistent with declared material type.

**Severity:** 🟡 Medium — Asset is usable but looks amateur. Material identity is lost.

---

### I-06 · Color Mud

**Description:**
Mixed or transitional colors lose their saturation and become dull, grey-brown, or lifeless — "mud." This happens when shading ramps are constructed by mixing colors toward black or white rather than rotating hue through the spectrum.

**Visual Symptoms:**
- Shadow colors that are simply darker, desaturated versions of the base color
- Mid-tones that appear grey or brown with no colorful identity
- Palette ramps that are straight lines in RGB space (black → color → white)
- Shading that looks "dirty" or "overworked" rather than atmospheric

**Root Cause:**
Straight value-only shading — darkening by adding black, lightening by adding white — kills saturation. Pixel art color ramps should follow hue rotation: shadows shift toward a cool/warm anchor (e.g., shadows rotate toward purple-blue; highlights toward yellow-cream). This is the "color ramp hue shift" principle that keeps colors vibrant across the value range.

**Corrective Principle:**
Construct palette ramps in HSB space with hue rotation: shadows shift hue toward the shadow anchor (cool: blue-violet; warm: orange-red), highlights shift toward the light anchor (typically yellow-white). Saturation should peak at the mid-tone, not at the base. Never mix toward pure black or pure white. Test ramps by placing them side by side against a known vivid reference.

**Automated Detection Hook:**
`palette_auditor.py` — ramp analysis mode; constructs palette ramps from clustered colors and checks each ramp for saturation collapse (saturation delta across ramp exceeds threshold in the wrong direction) and hue rotation presence. Reports mud risk score per ramp.

**Severity:** 🟠 Medium-High — Makes the entire sprite feel lifeless and low-quality even when the drawing is technically correct.

---

### I-07 · Jaggies / Staircase Artifact

**Description:**
Diagonal lines and curves display visible staircase patterns — uniform horizontal or vertical pixel steps — that make lines look mechanical and unnatural. Distinct from deliberate pixelation; these are unintended regularities in line construction.

**Visual Symptoms:**
- Diagonal lines composed of uniform N×1 or 1×N pixel steps with no variation
- Curves with repeating stair patterns instead of gradually changing step ratios
- Lines that "jitter" irregularly, neither smooth pixel-steps nor clean diagonals
- All diagonals appear at the same angle regardless of intended curvature

**Root Cause:**
Drawing diagonal lines at the pixel level requires deliberate step-ratio variation. A smooth-looking diagonal at 45° uses 1×1 steps; at 30° it uses 2×1 steps; at a less common angle it needs alternating step sizes. Without understanding pixel line theory, artists either get uniform stairs (mechanical) or irregular jitter (wobble) by drawing freehand.

**Corrective Principle:**
Learn pixel line theory: any diagonal line is defined by its step ratio (horizontal pixels : vertical pixels). For a consistent angle, the ratio must be consistent. For a curve, the ratio must gradually change. Use line tools set to pixel-perfect mode, or draw manually with awareness of step ratios. Reference the pixel art line angle chart — commit the common ratios to memory (1:1, 2:1, 3:1, 3:2, etc.).

**Automated Detection Hook:**
`outline_checker.py` — jaggies detector; runs along outline paths and measures step ratio regularity. Flags lines where step ratios have high variance (jitter) or where identical step ratios extend for too many consecutive steps at a non-45° angle (uniform staircase). Also detects "bent" lines with unintended direction changes.

**Severity:** 🟠 Medium-High — Degrades perceived craft significantly; visible even to non-pixel-art audiences.

---

## Tier 3 — Advanced Failures

*These failures occur in artists who have mastered the fundamentals but are working at a production scale, on animation, or in maintaining style consistency across a large asset library. They require system-level thinking, not just per-sprite craft.*

---

### A-01 · DNA Drift

**Description:**
An asset's visual identity gradually diverges from the project's established style over time or across revisions — changes accumulate in small, individually-justifiable increments until the asset no longer matches the style guide or original design specification. The asset has "drifted" from its DNA.

**Visual Symptoms:**
- Asset is clearly the same character/object but feels "off" compared to older versions
- Color ramps have shifted — different hue rotation, different number of steps
- Outline weight changed (1px to 2px, or selective outlining added/removed inconsistently)
- Proportions subtly different from established sprite sheet
- Comparison to spec sheet shows multiple small deviations, none individually alarming

**Root Cause:**
Each revision corrects a specific issue without reference to the whole-system baseline. Over N revisions, each locally-correct change compounds into global drift. Particularly problematic when multiple artists work on the same asset, or when an artist revisits old work with evolved skills and unconsciously applies new habits. No diff system is in place to catch gradual change.

**Automated Detection Hook:**
`rubric_scorer.py` — DNA drift checker; compares current asset against the registered baseline version in the asset registry. Reports pixel-level diff, palette delta (new/removed colors), outline profile comparison, and proportion bounding-box comparison. Flags assets where cumulative change score exceeds drift threshold, even if no single change is flagged individually.

**Corrective Principle:**
Maintain a locked "DNA reference" version of every base asset in the registry. Before committing any revision, run a mandatory drift check against the DNA reference. Diffs above threshold require explicit sign-off ("intentional redesign" flag). All style changes must come from the style guide, not from individual revision judgment.

**Severity:** 🔴 Critical — DNA drift silently breaks style cohesion across an entire project. By the time it's visible, hundreds of frames may be affected. It is the most expensive mistake to remediate at production scale.

---

### A-02 · Animation Rigidity

**Description:**
Animated sprites move but feel stiff and mechanical — joints rotate without squash/stretch, timing is uniform (every frame the same duration), and secondary motion (hair, clothing, accessories) is absent or ignored. The animation is technically correct but expressively dead.

**Visual Symptoms:**
- All animation frames display for identical duration (no timing variation)
- Character limbs pivot rigidly without any deformation at joint
- No anticipation or follow-through on major actions
- Secondary elements (cape, ears, tail) are either frozen or move in perfect sync with the body
- Sprite weight is not communicated — a heavy character falls at the same speed as a light one

**Root Cause:**
Artists animate by rotating/translating parts without understanding animation principles. They think of animation as "pose A → pose B" rather than as a performance with timing, weight, and physics. Pixel art animation is particularly prone to rigidity because the small canvas discourages squash/stretch (it's hard to do in 16px), and frame-by-frame work is labor intensive, tempting artists to use the minimum number of frames.

**Corrective Principle:**
Study the 12 principles of animation — even at pixel scale, squash/stretch, anticipation, and follow-through apply. Use timing variation: a fast strike might be 2 frames, recovery 6 frames. Add even one pixel of secondary motion to accessories. Use "smear frames" (single frames of motion blur) for fast actions. Reference real motion: photograph or video reference gives timing data even when anatomy reference is unavailable.

**Automated Detection Hook:**
`animation_linter.py` — primary tool; checks frame duration uniformity (all-same-duration flag), measures bounding box size variance across frames (low variance = no squash/stretch), detects keyframes where secondary element positions are unchanged relative to body (secondary motion freeze), and reports minimum/maximum frame durations.

**Severity:** 🟠 Medium-High — Animation is a core deliverable; rigidity is immediately perceptible to players and breaks immersion.

---

### A-03 · Selective Outlining Inconsistency

**Description:**
Selective outlining — the advanced technique of removing or lightening outline pixels where a form edge faces the light source, or where two forms of similar value meet — is applied inconsistently: present on some edges but randomly absent/present on others within the same sprite or asset set.

**Visual Symptoms:**
- Some edges have full black outlines; adjacent edges have none
- Outline removal does not correspond to any consistent light direction
- Interior edge lines between forms have outlines on one side but not the other
- Outline presence/absence varies frame-to-frame on surfaces not in motion

**Root Cause:**
Selective outlining requires active decision-making on every edge of every form. Artists learn the technique and apply it enthusiastically on some edges then forget to maintain it consistently, or apply it in areas where the lighting logic doesn't support it. Without a documented decision rule for each edge type, application becomes arbitrary.

**Corrective Principle:**
Document the selective outlining rule set in the sprite spec: which edge types get full outline, which get lightened outline (outline in form color), which get no outline. The rule must be derivable from light direction and edge type (silhouette vs. interior edge). Apply the rule mechanically and then check every edge against it before finalizing. Cross-frame: the rule must produce consistent results for static surfaces.

**Automated Detection Hook:**
`outline_checker.py` — selective outline consistency check; classifies each outline pixel as silhouette or interior edge, maps it against the declared light source angle, and checks whether outline presence/absence matches the expected pattern. Flags edges where the pattern violates the light source logic or is inconsistent across frames.

**Severity:** 🟡 Medium — Inconsistency is noticed subliminally; the asset looks "off" without viewers knowing why.

---

### A-04 · Hue Shift Ramp Errors

**Description:**
Palette ramps are constructed with hue shifts that are incorrect in direction or magnitude — shifting toward the wrong temperature anchor, shifting too aggressively (making shadows look tinted rather than dark), or shifting inconsistently across different ramps in the same palette.

**Visual Symptoms:**
- Shadows have a visible colored tint that competes with the form color (e.g., green shadows on a red character)
- Highlights desaturate to near-white instead of shifting toward a warm/cool anchor
- Different ramps in the same palette shift in opposite hue directions
- Shadow or highlight colors, when isolated, appear to belong to a different palette

**Root Cause:**
Hue shift is a known principle, but the direction and amount require calibrated judgment. Without color theory grounding, artists either shift too far (oversaturated tinted shadows), too little (mud), or in the wrong direction (arbitrary). Inconsistency across ramps happens when each ramp is built in isolation without a global palette temperature strategy.

**Corrective Principle:**
Establish a global palette temperature strategy: is the light source warm or cool? This determines highlight hue shift direction. The shadow anchor is typically the complementary temperature. Set hue shift magnitude limits: no more than 30° hue rotation from base to shadow, 20° from base to highlight. Build all ramps against the same temperature framework. Test by viewing all ramps simultaneously.

**Automated Detection Hook:**
`palette_auditor.py` — ramp hue shift analyzer; constructs detected ramps and measures hue rotation direction and magnitude at each step. Flags ramps where shadow steps shift in the wrong temperature direction relative to the declared light temperature, and where ramps within the same palette have inconsistent shift directions.

**Severity:** 🟠 Medium-High — Incorrect hue shifts create color mud or tinting that degrades the entire palette system.

---

### A-05 · Sub-Pixel Anatomy Errors

**Description:**
At very small sprite sizes (8×8, 12×12, 16×16), the artist attempts to render anatomical detail that requires more pixels than are available, resulting in features that are correct in intent but wrong in pixel-art translation — a face with four features where resolution allows only two readable ones, or fingers on a hand that should be read as a mitten.

**Visual Symptoms:**
- Faces on tiny sprites with all features (eyes, nose, mouth, ears) resulting in noise
- Hands with individual fingers at a scale where a flat mitten shape would read better
- Clothing seams, buttons, or details that appear as orphan pixels at this resolution
- Feature placement that is anatomically correct but reads as a blotch at sprite scale

**Root Cause:**
Artists scale down a design without rethinking it for the resolution. The solution is not to shrink the detail but to replace it with pixel-art resolution-appropriate abstraction. A 2-pixel eye on a 16px face is iconic; attempting a 1-pixel iris within it is beyond resolution. Without understanding resolution abstraction, every small sprite becomes an overcrowded mess.

**Corrective Principle:**
For each sprite resolution, define the maximum readable detail level — this is the "resolution budget." At 16px height: faces get 2 pixels for eyes, no nose pixel (implied by spacing), 1 pixel for mouth. At 32px: eyes can have pupils, basic nose implied by shadow. Never attempt to render a feature that requires more pixels than are available — instead, use the minimum pixel count that *implies* the feature. Simplification is craft, not failure.

**Automated Detection Hook:**
`rubric_scorer.py` — resolution budget checker; detects sprite pixel dimensions, looks up the project's resolution budget table, and flags detected feature regions (face, hand, etc.) that appear to contain more detail elements than the budget allows. Uses connected component analysis on feature regions.

**Severity:** 🟡 Medium — At small sizes, the sprite is unreadable. At medium sizes, it reads as amateur overworking.

---

### A-06 · Cross-Sprite Palette Inconsistency

**Description:**
Different sprites within the same scene, tileset, or character roster use incompatible palette systems — different shadow color temperatures, different numbers of shading steps, or entirely different color choices for shared environmental elements (all sprites should share the same sky color, dirt color, etc.).

**Visual Symptoms:**
- Placing two characters side by side reveals different skin tone strategies
- Environmental tiles use a different shadow temperature than character sprites
- Sprites that "should" share a color (e.g., all wood is the same brown) use slightly different browns
- A new sprite looks correct in isolation but wrong when placed in the game scene

**Root Cause:**
Sprites are created in isolation without constant reference to the master palette. Without enforced palette sharing, each artist (or each session) makes independent color decisions that are locally reasonable but globally inconsistent. Production scales this problem: the more sprites, the more drift from the system palette.

**Corrective Principle:**
Enforce a master palette file (e.g., `AM_PIXEL_MASTER.pal`) that all sprites must source their colors from. Any color not in the master palette is a violation. Shared environmental colors (wood, stone, sky, water) are defined once in the master palette and never re-created per sprite. Palette additions require review and update of the master file, not local improvisation.

**Automated Detection Hook:**
`palette_auditor.py` — cross-sprite consistency checker; loads all sprites in a scene/roster and identifies colors that are unique to a single sprite (potential violations) vs. shared across sprites. Compares all sprite palettes against the registered master palette file and reports deviation counts and specific violating colors.

**Severity:** 🔴 Critical — Cross-sprite inconsistency is immediately visible in-game and signals total breakdown of the asset pipeline's quality control.

---

## Quick Reference — Failure Mode Index

**B-01** · Pillow Shading → `rubric_scorer.py` (shading ring detector) → 🔴 High
**B-02** · Pure Black Outlines → `outline_checker.py` (black pixel scan) → 🟠 Medium-High
**B-03** · Anti-Aliasing Misuse → `outline_checker.py` (AA color validator) → 🟡 Medium
**B-04** · Orphan Pixels → `rubric_scorer.py` (isolated pixel detector) → 🟡 Medium
**B-05** · Proportion Errors → `rubric_scorer.py` (cross-frame proportion) → 🟠 Medium-High
**B-06** · Readability Failures → `rubric_scorer.py` (silhouette clarity) → 🔴 High
**I-01** · Color Banding → `banding_detector.py` (band width uniformity) → 🟠 Medium-High
**I-02** · Incorrect Dithering → `banding_detector.py` (dither pattern analysis) → 🟡 Medium
**I-03** · Palette Bloat → `palette_auditor.py` (unique color count) → 🟠 Medium-High
**I-04** · Inconsistent Light Source → `rubric_scorer.py` (highlight centroid drift) → 🔴 High
**I-05** · Texture Noise → `rubric_scorer.py` (entropy + autocorrelation) → 🟡 Medium
**I-06** · Color Mud → `palette_auditor.py` (saturation collapse check) → 🟠 Medium-High
**I-07** · Jaggies / Staircase → `outline_checker.py` (step ratio variance) → 🟠 Medium-High
**A-01** · DNA Drift → `rubric_scorer.py` (baseline diff, drift score) → 🔴 Critical
**A-02** · Animation Rigidity → `animation_linter.py` (timing + deformation analysis) → 🟠 Medium-High
**A-03** · Selective Outlining Inconsistency → `outline_checker.py` (light-angle vs outline map) → 🟡 Medium
**A-04** · Hue Shift Ramp Errors → `palette_auditor.py` (ramp hue rotation direction) → 🟠 Medium-High
**A-05** · Sub-Pixel Anatomy Errors → `rubric_scorer.py` (resolution budget check) → 🟡 Medium
**A-06** · Cross-Sprite Palette Inconsistency → `palette_auditor.py` (master palette deviation) → 🔴 Critical

---

## Severity Key

| Rating | Label | Meaning |
|---|---|---|
| 🔴 | High / Critical | Asset is broken, style-incoherent, or pipeline-failing. Must fix before shipping. |
| 🟠 | Medium-High | Noticeably degrades quality or consistency. Fix before milestone review. |
| 🟡 | Medium | Polish issue. Does not block function but signals skill gap. Fix in revision pass. |
| 🟢 | Low | Minor. Acceptable in early drafts; address in final polish. |

---

*AM Pixel Mistake Taxonomy | Phase 1 Boot Training | v1.0*
