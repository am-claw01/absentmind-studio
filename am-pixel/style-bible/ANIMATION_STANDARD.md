# AM Pixel — Animation Standard
**Style Bible | Phase 2 | LOCKED**

---

## Table of Contents

1. [Overview & Purpose](#overview--purpose)
2. [Required Animation Sets by Character Type](#required-animation-sets-by-character-type)
3. [Frame Count Specifications](#frame-count-specifications)
4. [Timing Conventions](#timing-conventions)
5. [Walk Cycle Construction](#walk-cycle-construction)
6. [Squash & Stretch Guidelines](#squash--stretch-guidelines)
7. [8-Directional vs 4-Directional Movement](#8-directional-vs-4-directional-movement)
8. [NPC Idle Loop Standards](#npc-idle-loop-standards)
9. [Battle Sprite Animations](#battle-sprite-animations)
10. [Naming Conventions](#naming-conventions)

---

## 1. Overview & Purpose

This document locks the animation requirements for all character and entity sprites in the AM Pixel project. All animators and technical artists must adhere to these specifications. Deviations require a formal revision to this document — do not silently vary frame counts or timing without updating this standard.

The target aesthetic is a retro RPG feel grounded in SNES-era conventions, with modern clarity. Animation should communicate intent clearly and read well at small sprite sizes. Every frame must earn its place.

---

## 2. Required Animation Sets by Character Type

### 2.1 Hero / Player Character

The player character receives the fullest animation set. All entries marked **[REQUIRED]** are mandatory for a shippable build. Entries marked **[OPTIONAL]** may be deferred to polish pass.

| Animation | Status |
|---|---|
| Walk (4 directions) | REQUIRED |
| Idle (standing) | REQUIRED |
| Run / Dash | REQUIRED |
| Attack — basic melee | REQUIRED |
| Attack — special / charged | REQUIRED |
| Hurt / Flinch | REQUIRED |
| Death | REQUIRED |
| Interact / Use item | REQUIRED |
| Battle idle (breathing) | REQUIRED |
| Battle attack | REQUIRED |
| Battle hurt | REQUIRED |
| Battle death | REQUIRED |
| Victory / celebration | OPTIONAL |
| Push / pull object | OPTIONAL |
| Sit / rest | OPTIONAL |
| Jump (if platformer elements used) | OPTIONAL |

### 2.2 NPC — Town / Friendly

NPCs require minimal sets. Their role is ambient life — they must feel inhabited without drawing focus from gameplay.

| Animation | Status |
|---|---|
| Idle loop | REQUIRED |
| Walk (2–4 directions depending on patrol needs) | REQUIRED |
| Talk / gesture (head bob or arm raise) | REQUIRED |
| Hurt | REQUIRED (for interactable NPCs) |
| Unique contextual animation (sweeping, fishing, etc.) | OPTIONAL |

> **Note:** NPCs that never leave a fixed position may reduce walk directions to 1 or 2 (facing camera + one side). Confirm with design before cutting.

### 2.3 Enemy — Small

Small enemies are numerous. Keep animation sets lean but readable. Every enemy must have a clear attack tell.

| Animation | Status |
|---|---|
| Idle | REQUIRED |
| Walk / Move (toward player) | REQUIRED |
| Attack | REQUIRED |
| Hurt / Flinch | REQUIRED |
| Death | REQUIRED |
| Alert (spot player) | OPTIONAL |

### 2.4 Enemy — Large

Large enemies justify a bigger animation budget. They should feel heavy and telegraphed.

| Animation | Status |
|---|---|
| Idle | REQUIRED |
| Walk / Move | REQUIRED |
| Attack — primary | REQUIRED |
| Attack — secondary (if applicable) | REQUIRED |
| Hurt / Flinch | REQUIRED |
| Stagger (significant damage reaction) | REQUIRED |
| Death | REQUIRED |
| Alert / Roar | OPTIONAL |

### 2.5 Boss

Bosses receive the largest animation budget. All phases must be fully specified in the design doc before animation begins. Do not start boss animation work without a locked phase breakdown.

| Animation | Status |
|---|---|
| Idle (per phase) | REQUIRED |
| Walk / Move (per phase, if applicable) | REQUIRED |
| Attack — each distinct attack type | REQUIRED |
| Hurt / Flinch | REQUIRED |
| Phase transition | REQUIRED |
| Enrage / buff animation | REQUIRED (if mechanic exists) |
| Stagger / vulnerable state | REQUIRED |
| Death sequence | REQUIRED |
| Intro / entrance | REQUIRED |
| Victory taunt (if player dies) | OPTIONAL |

> **Rule:** Boss death sequences must be a minimum of 6 frames and are encouraged to be full mini-cutscenes handled as a separate sprite sheet.

---

## 3. Frame Count Specifications

These counts are **locked**. Do not deviate without a documented revision. Frame counts refer to unique drawn frames — engine-side holds/repeats are separate from the art deliverable.

### 3.1 Walk Cycle

- **Standard:** 4 directions × 3 frames each = **12 frames total**
  - Directions: Down (South), Up (North), Left (West), Right (East)
  - Frame roles: Contact → Down → Passing (these three loop; the Up frame is implicit in the loop-back to Contact)
  - Export each direction as its own row on the sprite sheet
- **4-Frame Variant:** Permitted for hero and large enemies where richer locomotion is justified
  - 4 directions × 4 frames each = **16 frames total**
  - Frame roles: Contact → Down → Passing → Up (explicit)
  - Must be approved by lead before use — this is not the default

> **When to use the 4-frame variant:** Use it for the hero character and any boss/large enemy that has a prominent walk as part of their screen presence. For small enemies that swarm, use the 3-frame standard.

### 3.2 Idle

- **Range:** 2–4 frames
- **Default for most characters:** 2 frames (weight shift or breathing)
- **NPCs with personality:** Up to 4 frames
- Idle animations loop seamlessly — frame 1 and the final frame must not create a visible pop on loop

### 3.3 Attack

Frame count depends on attack archetype:

| Attack Type | Frame Count | Notes |
|---|---|---|
| Quick jab / light strike | 3 frames | Windup (1f), Hit (1f), Recovery (1f) |
| Standard melee swing | 4 frames | Windup (1–2f), Hit (1f), Recovery (1–2f) |
| Heavy / charged strike | 5–6 frames | Extended windup telegraphs the hit |
| Projectile launch | 3–4 frames | Windup, Release, Recovery |
| AOE / spell cast | 5–6 frames | Includes distinct cast gesture |

> **Rule:** The hit frame must always be a single, clearly distinct frame. Never blur or blend the impact pose — it must read as a still image for at least 1 drawn frame.

### 3.4 Hurt / Flinch

- **Range:** 2–3 frames
- **2-frame standard:** Flinch-back (1f) + Recovery (1f)
- **3-frame for heavier hits:** Pre-flinch (1f) + Full recoil (1f) + Recovery (1f)
- The flinch frame must show clear displacement from the idle/walk position — minimum 2px offset on the character's center of mass

### 3.5 Death

- **Range:** 4–6 frames
- **Minimum (small enemies):** 4 frames
- **Standard (hero, large enemies):** 5–6 frames
- Deaths must read clearly when played at the standard frame rate. Avoid pasting one frame identically — each frame must advance the collapse/dissolve/fall
- The final frame (death pose) is held by the engine; design it as a stable sprite

### 3.6 Victory / Celebration

- **Status:** Optional
- **Range:** 4–6 frames if implemented
- Loopable or one-shot — specify per character in the sprite sheet notes
- Hero victory animation plays in the world map / overworld context; it should be readable at the standard world sprite scale

### 3.7 Battle Sprite Animations

Battle sprites are the larger, side-facing sprites used in turn-based combat screens. These follow different rules from overworld sprites.

See Section 9 for full detail.

---

## 4. Timing Conventions

All timing is specified in frames at a **base rate of 60fps**. Equivalent timings at retro framerates are provided for reference and for any engine mode that targets a locked retro refresh.

### 4.1 Base Timing Table

| Duration Feel | Frames @ 60fps | Frames @ 20fps | Frames @ 15fps |
|---|---|---|---|
| Snap / instant | 2–3f | 1f | 1f |
| Fast | 4–6f | 1–2f | 1f |
| Snappy / responsive | 6–10f | 2–3f | 1–2f |
| Normal / standard | 10–18f | 3–6f | 2–4f |
| Slow / heavy | 18–30f | 6–10f | 4–7f |
| Very slow / boss weight | 30–48f | 10–16f | 7–12f |

### 4.2 Retro Framerate Notes

- **15fps (SNES-style):** Sprite animation updates every 4 display frames. This is the target aesthetic for overworld walk cycles and standard enemy movement. All 3-frame walk cycles are designed to read correctly at this rate.
- **20fps (smoother retro):** Sprite animation updates every 3 display frames. Used for attack and hurt animations where responsiveness matters more than aesthetic fidelity.
- **60fps (native):** UI elements, particle effects, and any screen-flash effects run at native 60fps regardless of the sprite animation rate.

> **Rule:** Never animate overworld walk cycles at greater than 20fps effective update rate. The chunky, stepped motion is part of the visual identity. Smooth interpolation between walk frames is **prohibited**.

### 4.3 Animation Hold Rules

- Windup frames on attacks: hold for **2–3 display frames** at 60fps (gives the player time to read the telegraph)
- Hit frames: hold for **1–2 display frames** at 60fps
- Death final frame: hold **indefinitely** until engine removes the entity
- Idle frame transitions: **no hold** — step through at the standard sprite framerate

---

## 5. Walk Cycle Construction

### 5.1 The Four Keyframes

Even in the 3-frame export, animators must conceptually block all four keyframes before reducing. Understanding all four produces a better 3-frame result.

**Contact Frame**
- Both feet have just made or are making contact with the ground
- The leading foot is fully extended forward; the trailing foot pushes off at the back
- The body is at its natural height — this is the "neutral" vertical position
- Arms are at maximum swing extension in opposition to feet

**Down Frame**
- The body weight drops onto the leading foot
- The body reaches its **lowest point** in the cycle — typically 1–2px below the contact frame
- The knees are slightly bent, absorbing impact
- Arms cross through center

**Passing Frame**
- The trailing leg swings forward and passes the planted leg
- The body reaches its **highest point** in the cycle — typically 1px above contact frame
- One arm is forward, one back, both near neutral
- This is often the most distinctive silhouette frame — make it read clearly

**Up Frame** *(explicit in 4-frame variant; implied in 3-frame)*
- The heel of the rear foot is lifting; the character is in mid-stride
- Body at slightly above neutral height
- In the 3-frame cycle, this moment is captured by looping back from Passing to Contact — the engine's frame hold creates the implied "up" moment

### 5.2 3-Frame Walk Cycle Layout

```
Frame 1: Contact (right foot leads)
Frame 2: Down / Pass combined — body at low point, feet mid-swap
Frame 3: Contact (left foot leads) — mirrored from Frame 1
[Loop back to Frame 1]
```

> For pixel sprites under 32px tall, the vertical bob should be **1px maximum**. For sprites 32–64px tall, **1–2px**. For large/boss sprites above 64px, **2–3px**. Do not exaggerate walk bounce beyond these values — it reads as a cartoon hop rather than a walk at small scales.

### 5.3 Directional Walk Consistency

- The **down-facing (South) walk** is the anchor animation. Draw this first.
- **Up-facing (North) walk:** Show the back of the character. The silhouette rhythm must match the South walk's timing. If the character has a distinctive cloak, hat, or back detail, this is the frame to showcase it.
- **Side-facing (East) walk:** Drawn in full profile. This is often the most animation-rich direction — both arm and leg swing are visible.
- **West walk:** Mirror of East. Check for asymmetric details (holsters, badges, scars) and adjust accordingly. Do not simply flip without reviewing.

---

## 6. Squash & Stretch Guidelines

Squash and stretch exists in pixel art but operates under strict constraints. Pixel art squash/stretch is **structural**, not fluid — achieved through deliberate frame composition, not interpolation.

### 6.1 Permitted Techniques

- **Vertical compression on landing:** Reduce sprite height by 1–2px on the Down frame of a walk or landing frame of a jump. Compensate with +1px width addition at the widest point to preserve approximate pixel mass.
- **Vertical extension on attack windup:** Extend the body upward 1px on a dramatic windup. Never more than 1px on characters under 48px tall.
- **Limb elongation on reach:** A punching arm or swinging leg may extend 1–2px beyond its idle proportion. This should be a single frame (the hit/contact frame) and immediately return.

### 6.2 Prohibited Techniques

- **Fractional-pixel squash:** Do not attempt to simulate sub-pixel squash/stretch. Every pixel must sit on the grid.
- **Body distortion across multiple frames:** Squash/stretch is a single-frame accent. A character should not sustain a deformed body shape for more than 1–2 frames.
- **Stretching the head:** Head size is fixed. Do not alter head pixel dimensions for squash/stretch. The body and limbs absorb all deformation.
- **Scaling transforms:** Never use engine-side scale transforms to achieve squash/stretch on character sprites. It must be drawn.

### 6.3 Impact Frames

Every attack that makes contact should have one **impact frame** where the attacker's body shows the force feedback: a slight backward lean, shoulder rotation, or ground-plant stance. This is distinct from squash/stretch — it's weight and force expression, not dimensional change.

---

## 7. 8-Directional vs 4-Directional Movement

### 7.1 Default: 4-Directional

The AM Pixel project defaults to **4-directional movement** for all characters. All required animation sets are specified for 4 directions. This is the SNES-era canonical choice and the one this style is built around.

### 7.2 8-Directional Handling (If Implemented)

If an 8-directional movement system is added (design decision, not an art default), the following rules apply:

- **Do not draw diagonal-specific walk sprites.** Diagonal movement uses the side-facing sprite (East or West), with the engine selecting based on the dominant axis of movement.
- **Diagonal idle:** Use the side-facing idle sprite. Never create a separate diagonal idle.
- **Exception — boss intro cinematics:** A boss may have a single diagonal-approach pose used only in a scripted entrance. This is a posed sprite, not an animation loop, and must be flagged as such in the sprite sheet.

### 7.3 Axis Priority Rule

When diagonal input is detected, the engine must enforce an **axis priority**:
- If vertical component > horizontal: use North or South sprite
- If horizontal component ≥ vertical: use East or West sprite
- This decision is the engine's responsibility — art does not provide diagonal blends

> **Art note:** When drawing side-facing sprites, ensure they read cleanly both when the character moves purely sideways AND when diagonal movement is happening. Exaggerated forward lean on the side walk can look strange in diagonal contexts — keep the side walk silhouette relatively upright.

---

## 8. NPC Idle Loop Standards

NPCs are ambient. Their idle animations must signal life without demanding attention. An NPC that moves too much becomes a visual distraction and pulls focus from gameplay and narrative elements.

### 8.1 Motion Budget

| NPC Type | Max Pixel Displacement | Max Unique Frames |
|---|---|---|
| Background ambient (crowd filler) | 1px vertical bob only | 2 frames |
| Standard town NPC | 1–2px vertical, slight head turn | 2–3 frames |
| Key NPC / story character | 2px vertical, arm/head gesture | 3–4 frames |
| Quest-giver NPC (animated emphasis) | 2–3px, full upper body gesture | 4 frames max |

### 8.2 The 1–2 Pixel Bob

The default NPC idle is a **2-frame vertical bob of 1px**:
- Frame 1: Base position
- Frame 2: 1px up (shift the entire sprite up by 1px; the bottom row becomes empty/transparent)
- Loop: Frame 1 → Frame 2 → Frame 1

This alone is enough to make a town feel populated without creating visual noise. Resist the urge to add more movement unless design explicitly requires it.

### 8.3 Phase Offset for Crowds

When multiple NPCs share the same idle animation, they must be **phase-offset** in the engine. NPCs sharing the exact same loop frame create an eerie synchronized bobbing effect. Standard offset values:

- 2 NPCs on screen: offset second NPC by 50% of loop length
- 3+ NPCs: distribute offsets evenly across the loop length
- This is an engine/implementation note, but the sprite sheet must clearly specify loop length so programmers can calculate offsets

### 8.4 NPC Contextual Animations

Some NPCs have a single contextual animation (a blacksmith hammering, a vendor waving). Rules:

- The contextual animation must loop cleanly
- It should play as the default idle — the NPC is always "doing their thing"
- If the NPC also needs a standard idle (e.g., they look up when talked to), provide both and specify the transition logic in the notes column of the sprite sheet

---

## 9. Battle Sprite Animations

Battle sprites are large, side-facing representations used in the turn-based combat interface. They follow separate rules from overworld sprites.

### 9.1 Battle Idle — Breathing

- **Frame count:** 4–6 frames
- **Motion:** Subtle vertical expansion and contraction to simulate breathing
- This loop must be seamless and run continuously during the character's or enemy's idle state in battle
- Pixel displacement: chest/torso rises **1–2px** at peak inhale; returns to base
- Do not animate the head separately from the body in the breathing loop — keep it as one unified mass shift

### 9.2 Battle Attack

The battle attack animation is broken into three explicit phases. Each phase must be identifiable as a distinct beat:

**Windup / Anticipation**
- 1–2 frames
- Character leans back, charges, or raises weapon
- This is the telegraph — it must be visually distinct from idle

**Hit / Action**
- 1–2 frames
- The attack fires, strikes, or releases
- If a projectile is involved, the projectile is a separate sprite — the character sprite shows the release/cast pose
- The hit frame is the most exaggerated pose in the animation

**Recovery**
- 1–2 frames
- Character returns toward idle
- Can be a straight return or a brief "follow-through" pose before settling

> **Total battle attack frame count:** 3–6 frames depending on attack type. Match the overworld attack timing guidelines from Section 3.3.

### 9.3 Battle Hurt

- **Frame count:** 2–3 frames
- Knockback or impact reaction
- Must clearly differ from idle — minimum 3–4px displacement on large battle sprites
- Frame 1: Impact (displaced from rest position)
- Frame 2: Recovery lean
- Frame 3 (optional): Return to idle (or the idle loop handles re-settling)

### 9.4 Battle Death

- **Frame count:** 4–6 frames minimum
- Enemy deaths: collapse, dissolve, or shatter — specify per enemy type in their individual design doc
- Hero death: solemn fall — reference design doc for hero
- The final frame of a death animation is the "dead" sprite and may be held or faded by the engine — design it as a stable composition

### 9.5 Battle Sprite Size Reference

| Sprite Role | Approximate Size | Notes |
|---|---|---|
| Hero (battle) | 48×64px or 64×64px | Confirm with UI layout |
| Small enemy | 32×32px to 48×48px | — |
| Large enemy | 64×64px to 80×96px | — |
| Boss | 96×96px to 128×128px or wider | May require multiple sprite sheets |

These are reference dimensions — confirm against the active UI layout doc before beginning battle sprite work.

---

## 10. Naming Conventions

All sprite sheet files and individual animation exports must follow this naming format:

```
[character_id]_[animation_name]_[direction]_[variant].png
```

**Examples:**
```
hero_walk_south_3f.png
hero_walk_south_4f.png          ← 4-frame variant, explicitly flagged
orc_small_death_01.png
boss_dragon_attack_phase2.png
npc_blacksmith_idle.png
hero_battle_attack_windup.png
```

**Direction codes:** `north`, `south`, `east`, `west`
**Animation name tokens (standard):** `idle`, `walk`, `run`, `attack`, `hurt`, `death`, `victory`, `battle_idle`, `battle_attack`, `battle_hurt`, `battle_death`, `transition`

> Any animation not covered by the standard tokens must be documented in the character's individual sprite sheet notes file, located alongside the sprite sheet in the asset directory.

---

## Revision Log

| Version | Date | Author | Change Summary |
|---|---|---|---|
| v1.0 | 2026-05-09 | AM Studio | Initial lock |

---

*AM Pixel Animation Standard | Style Bible v1.0 | LOCKED*
