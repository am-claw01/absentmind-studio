#!/usr/bin/env python3.14
"""
tools/class_labeler.py
=======================
CHANGE-034 — Multi-Class Semantic Labeling

Assigns sprite_class + sprite_subclass to every sprite_XXXX.json in the corpus
using keyword rules derived from pack name and path structure.

Class taxonomy:
  character   (humanoid / monster / creature / npc)
  tileset     (terrain / structure / dungeon / interior / exterior)
  environment (tree / rock / plant / water / structure / prop)
  effect      (particle / projectile / explosion / magic / weather)
  ui          (button / icon / panel / cursor / hud)
  item        (weapon / armor / consumable / key_item / treasure)
  vehicle     (ground / air / water / space)
  unknown     (no rule fired confidently — never forced)

Written fields in sprite_XXXX.json:
  sprite_class      : str
  sprite_subclass   : str | null
  class_confidence  : float  (0.0–1.0)
  class_rule_matched: str    (rule that fired, e.g. "pack_keyword:character")

Approval gate: unknown rate < 15% required before Phase 4 training.
If unknown rate > 15%: report driving packs, propose rule additions, do NOT retry blindly.

Usage:
  python tools/class_labeler.py [--corpus data/corpus/train] [--dry-run]
  python tools/class_labeler.py [--corpus data/corpus/train] --apply
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT   = Path(__file__).parent.parent.resolve()
UNKNOWN_GATE   = 0.15   # Phase 4 gate: unknown rate must be below this


# ──────────────────────────────────────────────────────────────────────────────
# Rule definitions
# Each rule is (pattern, primary_class, subclass, confidence, rule_name)
# Patterns are matched against lowercased pack_name + "/" + lowercased path
# Rules are evaluated in order — first match wins
# ──────────────────────────────────────────────────────────────────────────────

# Format: (regex_pattern, primary, subclass, confidence, rule_name)
RULES: list[tuple[str, str, str | None, float, str]] = [

    # ── tileset_meta.json present → definitive tileset signal ─────────────────
    # (handled separately in code, not as a regex rule)

    # ── Dungeon Crawl tiles ────────────────────────────────────────────────────
    (r"dungeoncrawl|projectutumno|dcss|crawl.*tile|oga.*dungeon",
     "tileset", "dungeon", 0.90, "pack_keyword:dungeon_crawl"),

    # ── LPC (Liberated Pixel Cup) ──────────────────────────────────────────────
    (r"lpc.*base.*tile|lpc.*castle|lpc.*dungeon|lpc.*floor|lpc.*wall|lpc.*stair|lpc.*mountain|lpc.*cabinet|lpc.*interior|castlefloor|castlewall|castle_outside",
     "tileset", "structure", 0.90, "pack_keyword:lpc_tileset"),
    (r"lpc.*tree|lpc.*plant|lpc.*rock|lpc.*treetop",
     "environment", "tree", 0.85, "pack_keyword:lpc_environment"),
    (r"lpc.*character|lpc.*char|lpc.*human|lpc.*npc",
     "character", "humanoid", 0.85, "pack_keyword:lpc_character"),

    # ── Kenney packs ──────────────────────────────────────────────────────────
    (r"kenney.*medieval.*rts|medieval(environment|structure|tile|unit|prop|weapon|ruin)",
     "tileset", "exterior", 0.88, "pack_keyword:kenney_medieval_tile"),
    (r"kenney.*rpg.*urban|rpg.*urban.*pack|rpgtile\d+",
     "tileset", "interior", 0.85, "pack_keyword:kenney_rpg_urban"),
    (r"kenney.*tiny.*town|tiny.*town",
     "tileset", "exterior", 0.85, "pack_keyword:kenney_tiny_town"),
    (r"kenney.*pixel.*platformer.*background",
     "environment", "structure", 0.80, "pack_keyword:kenney_platformer_bg"),
    (r"kenney.*pixel.*platformer",
     "tileset", "terrain", 0.85, "pack_keyword:kenney_platformer_tile"),
    (r"kenney.*roguelike|micro.*roguelike",
     "tileset", "dungeon", 0.82, "pack_keyword:kenney_roguelike"),
    (r"kenney.*1.*bit",
     "tileset", "terrain", 0.75, "pack_keyword:kenney_1bit"),
    (r"kenney.*vehicle|kenney.*car|kenney.*ship|kenney.*plane",
     "vehicle", None, 0.90, "pack_keyword:kenney_vehicle"),
    (r"kenney.*ui|kenney.*button|kenney.*cursor|kenney.*hud",
     "ui", "button", 0.90, "pack_keyword:kenney_ui"),
    (r"kenney.*icon",
     "ui", "icon", 0.90, "pack_keyword:kenney_icon"),
    (r"kenney.*item|kenney.*weapon|kenney.*sword|kenney.*chest|kenney.*coin|kenney.*gem",
     "item", None, 0.85, "pack_keyword:kenney_item"),
    (r"kenney.*character|kenney.*player|kenney.*hero|kenney.*npc|kenney.*person",
     "character", "humanoid", 0.85, "pack_keyword:kenney_character"),
    (r"kenney.*enemy|kenney.*monster|kenney.*creature|kenney.*alien",
     "character", "monster", 0.85, "pack_keyword:kenney_enemy"),
    (r"kenney.*effect|kenney.*particle|kenney.*explosion|kenney.*magic",
     "effect", None, 0.85, "pack_keyword:kenney_effect"),

    # ── Path structure signals ─────────────────────────────────────────────────
    (r"/characters?/|/char/|/heroes?/|/player/|/npc/|/enemies?/|/monsters?/",
     "character", "humanoid", 0.80, "path_keyword:characters"),
    (r"/tiles?/|/terrain/|/map/|/tileset/|/floors?/|/walls?/|/grounds?/",
     "tileset", "terrain", 0.80, "path_keyword:tiles"),
    (r"/ui/|/hud/|/interface/|/buttons?/|/icons?/|/panels?/|/menus?/",
     "ui", "button", 0.80, "path_keyword:ui"),
    (r"/effects?/|/particles?/|/explosions?/|/magic/|/spells?/|/projectiles?/",
     "effect", "particle", 0.80, "path_keyword:effects"),
    (r"/items?/|/weapons?/|/swords?/|/armor/|/armour/|/shields?/|/potions?/|/keys?/|/chests?/",
     "item", "weapon", 0.80, "path_keyword:items"),
    (r"/vehicles?/|/cars?/|/ships?/|/planes?/|/aircraft/",
     "vehicle", None, 0.80, "path_keyword:vehicles"),
    (r"/environments?/|/nature/|/trees?/|/rocks?/|/plants?/|/props?/",
     "environment", "prop", 0.75, "path_keyword:environment"),
    (r"/backgrounds?/|/bg/",
     "environment", "structure", 0.70, "path_keyword:background"),

    # ── Generic pack name signals ──────────────────────────────────────────────
    (r"character|warrior|knight|mage|wizard|archer|rogue|thief|hero|player|enemy|monster|creature|beast|dragon|goblin|orc|troll|zombie|ghost|demon|angel|fairy|elf|dwarf|human|person|npc|mob",
     "character", None, 0.72, "pack_keyword:character"),
    (r"walk|run|idle|attack|death|hurt|jump|cast|spell|anim",
     "character", None, 0.68, "pack_keyword:animation"),
    (r"floor|wall|ground|terrain|tile|dungeon|cave|castle|interior|exterior|overworld|world|map|room|corridor",
     "tileset", None, 0.72, "pack_keyword:tileset"),
    (r"tree|forest|grass|plant|rock|stone|mountain|river|lake|water|cloud|bush|flower|nature|outdoor",
     "environment", None, 0.70, "pack_keyword:environment"),
    (r"explosion|fire|flame|smoke|spark|particle|magic|glow|lightning|bolt|beam|wave|effect|impact",
     "effect", None, 0.70, "pack_keyword:effect"),
    (r"sword|axe|spear|bow|gun|wand|staff|shield|armor|armour|helmet|potion|scroll|key|coin|gem|treasure|chest|item|loot",
     "item", None, 0.70, "pack_keyword:item"),
    (r"car|truck|ship|boat|plane|aircraft|helicopter|rocket|tank|vehicle|mech",
     "vehicle", None, 0.70, "pack_keyword:vehicle"),
    (r"button|icon|cursor|hud|menu|panel|bar|frame|window|ui|interface",
     "ui", None, 0.70, "pack_keyword:ui"),

    # ── Arkanos / specific known packs ────────────────────────────────────────
    (r"arkanos",
     "character", "monster", 0.82, "pack_keyword:arkanos_monsters"),
    (r"holek|preview_\d+",
     "character", "humanoid", 0.70, "pack_keyword:misc_character"),
    (r"simples_pimples|simple.*pimple",
     "character", "creature", 0.70, "pack_keyword:simples_pimples"),
    (r"rpg.*pack|rpg.*asset|rpg.*sprite",
     "character", None, 0.65, "pack_keyword:rpg_generic"),
]

# Subclass refinements: if primary class matched, check these for subclass
SUBCLASS_RULES: dict[str, list[tuple[str, str]]] = {
    "character": [
        (r"human|person|npc|villager|civilian|townsperson|blonde|black|grey|red|brown", "humanoid"),
        (r"monster|enemy|mob|boss|demon|orc|goblin|troll|zombie|undead|ghost|vampire", "monster"),
        (r"creature|beast|dragon|wolf|cat|dog|bird|fish|insect|slime|worm|spider", "creature"),
        (r"npc|merchant|shopkeeper|guard|soldier|knight|king|queen|wizard|mage", "npc"),
    ],
    "tileset": [
        (r"dungeon|cave|underground|crypt|sewer", "dungeon"),
        (r"castle|fort|wall|tower|battlement|stone|brick", "structure"),
        (r"indoor|interior|inside|room|floor|carpet|wood", "interior"),
        (r"outdoor|exterior|outside|street|road|path", "exterior"),
        (r"grass|sand|dirt|snow|lava|water|rock|terrain|ground", "terrain"),
    ],
    "environment": [
        (r"tree|forest|bush|shrub|log|stump", "tree"),
        (r"rock|stone|boulder|cliff|mountain", "rock"),
        (r"plant|flower|mushroom|cactus|seaweed", "plant"),
        (r"water|lake|river|ocean|puddle|waterfall", "water"),
        (r"building|house|shop|ruin|wall|structure", "structure"),
    ],
    "effect": [
        (r"particle|spark|dust|smoke|steam", "particle"),
        (r"projectile|bullet|arrow|bolt|missile|shot", "projectile"),
        (r"explosion|blast|boom|burst", "explosion"),
        (r"magic|spell|cast|glow|beam|wave|lightning", "magic"),
        (r"rain|snow|fog|cloud|weather", "weather"),
    ],
    "item": [
        (r"sword|axe|spear|bow|gun|wand|staff|dagger|blade|weapon", "weapon"),
        (r"armor|armour|shield|helmet|boots|glove|cloak|robe", "armor"),
        (r"potion|food|herb|berry|mushroom|consumable", "consumable"),
        (r"key|door|lock|lever|switch", "key_item"),
        (r"coin|gem|gold|treasure|chest|ring|amulet", "treasure"),
    ],
    "vehicle": [
        (r"car|truck|cart|horse|bike|cycle", "ground"),
        (r"plane|aircraft|helicopter|balloon|rocket|ship.*air|airship", "air"),
        (r"boat|ship|canoe|raft|sub|naval", "water"),
        (r"rocket|ufo|shuttle|space.*ship", "space"),
    ],
    "ui": [
        (r"button|btn|click|press", "button"),
        (r"icon|symbol|badge|emblem", "icon"),
        (r"panel|window|frame|border|box", "panel"),
        (r"cursor|pointer|arrow.*ui|crosshair", "cursor"),
        (r"hud|health|mana|bar|status|gauge", "hud"),
    ],
}


def classify_sprite(pack_name: str, rel_path: str, has_tileset_meta: bool) -> dict:
    """
    Classify a sprite by pack name and relative path.
    Returns dict: {sprite_class, sprite_subclass, class_confidence, class_rule_matched}
    """
    # Definitive: tileset_meta.json present
    if has_tileset_meta:
        return {
            "sprite_class":       "tileset",
            "sprite_subclass":    None,
            "class_confidence":   0.95,
            "class_rule_matched": "tileset_meta_present",
        }

    search_str = (pack_name + "/" + rel_path).lower()

    for pattern, primary, subclass, confidence, rule_name in RULES:
        if re.search(pattern, search_str):
            # Refine subclass if not already set
            if subclass is None and primary in SUBCLASS_RULES:
                for sub_pattern, sub_name in SUBCLASS_RULES[primary]:
                    if re.search(sub_pattern, search_str):
                        subclass = sub_name
                        break
            return {
                "sprite_class":       primary,
                "sprite_subclass":    subclass,
                "class_confidence":   confidence,
                "class_rule_matched": rule_name,
            }

    # No rule fired
    return {
        "sprite_class":       "unknown",
        "sprite_subclass":    None,
        "class_confidence":   0.0,
        "class_rule_matched": "no_rule_matched",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="CHANGE-034 multi-class semantic labeling")
    parser.add_argument("--corpus",  default=str(PROJECT_ROOT / "data" / "corpus" / "train"))
    parser.add_argument("--apply",   action="store_true",
                        help="Write sprite_class fields into sprite_XXXX.json. "
                             "Default (omit) is dry-run / report only.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Alias for scan/report-only mode (no writes)")
    parser.add_argument("--sample",  type=int, default=20,
                        help="Number of sample sprites to show per class in report")
    args = parser.parse_args()
    dry_run = not args.apply

    corpus_dir = Path(args.corpus)
    if not corpus_dir.exists():
        print(f"ERROR: corpus not found: {corpus_dir}", file=sys.stderr)
        sys.exit(1)

    print("Scanning corpus...", flush=True)
    json_files: list[Path] = []
    for root, dirs, files in os.walk(corpus_dir):
        dirs.sort()
        for fname in sorted(files):
            if (fname.endswith(".json")
                    and not fname.endswith("_seq.json")
                    and fname not in ("manifest.json", "tileset_meta.json")):
                json_files.append(Path(root) / fname)

    total = len(json_files)
    print(f"Found {total:,} sprite metadata files", flush=True)

    class_counts:    Counter = Counter()
    subclass_counts: dict[str, Counter] = defaultdict(Counter)
    unknown_packs:   Counter = Counter()
    pack_total:      Counter = Counter()
    samples: dict[str, list[str]] = defaultdict(list)

    already_labeled = 0
    written = 0
    report_every = 10_000

    for i, json_path in enumerate(json_files, 1):
        try:
            rel       = json_path.relative_to(corpus_dir)
            pack_name = rel.parts[0]
            rel_path  = str(rel)
        except (ValueError, IndexError):
            pack_name = json_path.parent.name
            rel_path  = json_path.name

        pack_total[pack_name] += 1

        try:
            meta = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Check if tileset_meta.json exists alongside
        has_tileset_meta = (json_path.parent / "tileset_meta.json").exists()

        # Skip if already labeled (idempotent)
        if "sprite_class" in meta:
            already_labeled += 1
            label = meta["sprite_class"]
            class_counts[label] += 1
            if meta.get("sprite_subclass"):
                subclass_counts[label][meta["sprite_subclass"]] += 1
            if label == "unknown":
                unknown_packs[pack_name] += 1
            if i % report_every == 0:
                print(f"  {i:,}/{total:,} processed...", flush=True)
            continue

        result = classify_sprite(pack_name, rel_path, has_tileset_meta)
        label  = result["sprite_class"]

        class_counts[label] += 1
        if result["sprite_subclass"]:
            subclass_counts[label][result["sprite_subclass"]] += 1
        if label == "unknown":
            unknown_packs[pack_name] += 1
        if len(samples[label]) < args.sample:
            samples[label].append(rel_path)

        if not dry_run:
            meta.update(result)
            json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            written += 1

        if i % report_every == 0:
            print(f"  {i:,}/{total:,} processed — {class_counts['unknown']:,} unknown so far...",
                  flush=True)

    # --- Report ---
    unknown_count = class_counts["unknown"]
    unknown_rate  = unknown_count / total if total else 0.0

    print("\n" + "=" * 60)
    print("CLASS LABELING REPORT")
    print("=" * 60)
    print(f"  Total sprites processed     : {total:,}")
    print(f"  Already labeled (skipped)   : {already_labeled:,}")
    print(f"  Written this run            : {written:,}" if not dry_run else "  (dry-run — no writes)")
    print()
    print("Class distribution:")
    for cls, count in sorted(class_counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        print(f"  {cls:<15}  {count:>8,}  ({pct:.1f}%)")
        if cls in subclass_counts:
            for sub, scnt in sorted(subclass_counts[cls].items(), key=lambda x: -x[1])[:5]:
                print(f"    ↳ {sub:<12}  {scnt:>7,}")
    print()

    gate_status = "✅ PASS" if unknown_rate < UNKNOWN_GATE else "❌ FAIL"
    print(f"  Unknown rate: {unknown_rate:.1%}  (gate: <{UNKNOWN_GATE:.0%})  {gate_status}")

    if unknown_rate >= UNKNOWN_GATE:
        print(f"\n⚠  Unknown rate {unknown_rate:.1%} exceeds Phase 4 gate ({UNKNOWN_GATE:.0%})")
        print("  Top packs driving unknowns:")
        for pack, cnt in unknown_packs.most_common(20):
            rate = cnt / pack_total[pack]
            print(f"    {pack:<60}  {cnt:>5,}/{pack_total[pack]:<5,}  ({rate:.0%})")
        print("\n  ACTION REQUIRED: Review above packs, propose rule additions, re-run after approval.")
        print("  Do NOT start Phase 4 training until unknown rate drops below 15%.")

    if dry_run:
        print("\n  *** DRY-RUN — no fields written ***")

    # Sample output per class
    print("\n" + "-" * 60)
    print(f"Sample sprites per class (up to {args.sample} each):")
    for cls in sorted(samples):
        print(f"\n  [{cls}]")
        for s in samples[cls]:
            print(f"    {s}")

    print("=" * 60)


# ── Public API for use at ingestion time ──────────────────────────────────────

def label_sprite(pack_name: str, rel_path: str, has_tileset_meta: bool) -> dict:
    """
    Compute and return class label dict for a sprite at ingestion time.
    Call this in run_pipeline.py / harvest_loop.py when writing sprite_XXXX.json.
    Returns: {sprite_class, sprite_subclass, class_confidence, class_rule_matched}
    """
    return classify_sprite(pack_name, rel_path, has_tileset_meta)


if __name__ == "__main__":
    main()
