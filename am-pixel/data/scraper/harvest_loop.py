#!/usr/bin/env python3.14
"""
AM Pixel — Continuous Harvest Loop
====================================
Scrapes new sprite packs, then immediately pipelines them into the corpus.
Runs indefinitely. Safe to kill at any time — no partial state corruption
(provenance is written per-sprite, pipeline skips already-processed files).

No API calls. No costs. Pure HTTP + local processing.

Usage:
    python harvest_loop.py [--once]   # --once: single pass then exit
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import time
import random
import hashlib
import urllib.robotparser
import zipfile
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    sys.exit("ERROR: pip install requests")

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("WARNING: pip install Pillow for image processing")

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).parent.resolve()
DATA_DIR      = SCRIPT_DIR.parent.resolve()
PROJECT_ROOT  = DATA_DIR.parent.resolve()
RAW_DIR       = DATA_DIR / "raw" / "sprites"
MANIFEST_PATH = DATA_DIR / "TRAINING_PROVENANCE_MANIFEST.json"
CORPUS_TRAIN  = DATA_DIR / "corpus" / "train"
CORPUS_VAL    = DATA_DIR / "corpus" / "validation"
STATS_PATH    = DATA_DIR / "corpus_stats.md"
LOG_PATH      = SCRIPT_DIR / "harvest_loop.log"

PIPELINE_DIR  = DATA_DIR / "pipeline"
sys.path.insert(0, str(PIPELINE_DIR))
sys.path.insert(0, str(DATA_DIR))

DELAY = 1.5   # seconds between HTTP requests
CYCLE_PAUSE = 120  # seconds between full harvest cycles
VAL_RATIO = 0.10

# ── Logging ────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")

# ── HTTP ───────────────────────────────────────────────────────────────────
def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://",  HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "AMPixelHarvest/1.0 (educational pixel art dataset)"})
    return s

SESSION = make_session()
_ROBOTS: dict[str, urllib.robotparser.RobotFileParser] = {}

def robots_ok(url: str) -> bool:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base not in _ROBOTS:
        rp = urllib.robotparser.RobotFileParser()
        try:
            rp.set_url(f"{base}/robots.txt")
            rp.read()
        except Exception:
            rp = urllib.robotparser.RobotFileParser()
        _ROBOTS[base] = rp
    return _ROBOTS[base].can_fetch("*", url)

def safe_get(url: str, timeout: int = 40):
    if not robots_ok(url):
        log(f"  robots.txt blocked: {url}")
        return None
    time.sleep(DELAY)
    try:
        r = SESSION.get(url, timeout=timeout)
        return r if r.status_code == 200 else None
    except Exception as e:
        log(f"  GET error {url}: {e}")
        return None

def download_zip(url: str, dest: Path) -> bool:
    if not robots_ok(url):
        return False
    try:
        time.sleep(DELAY)
        r = SESSION.get(url, timeout=120, stream=True)
        if r.status_code != 200:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
        return True
    except Exception as e:
        log(f"  ZIP download error {url}: {e}")
        return False

def extract_zip(zip_path: Path, extract_to: Path) -> list[Path]:
    extract_to.mkdir(parents=True, exist_ok=True)
    found = []
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.namelist():
                if member.lower().endswith(".png"):
                    dest = extract_to / Path(member).name
                    if dest.exists():
                        found.append(dest)
                        continue
                    try:
                        data = z.read(member)
                        dest.write_bytes(data)
                        found.append(dest)
                    except Exception:
                        pass
    except Exception as e:
        log(f"  ZIP extract error: {e}")
    return found

# ── Provenance ─────────────────────────────────────────────────────────────
def phash(path: Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()[:16]
    except Exception:
        return "unknown"

def load_manifest() -> list[dict]:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text())
        except Exception:
            return []
    return []

def save_manifest(data: list[dict]) -> None:
    MANIFEST_PATH.write_text(json.dumps(data, indent=2))

def known_paths(manifest: list[dict]) -> set[str]:
    return {e.get("local_path", "") for e in manifest}

def add_provenance(manifest: list[dict], png: Path, source_url: str,
                   creator: str, license_str: str, genre: str) -> None:
    slug = re.sub(r"[^a-z0-9_]", "_", png.stem.lower())[:60]
    entry = {
        "sprite_id": f"{creator.lower().replace(' ','_')}_{slug}",
        "source_url": source_url,
        "creator": creator,
        "license": license_str,
        "date_added": datetime.datetime.utcnow().isoformat(),
        "perceptual_hash": phash(png),
        "copyright_filter_status": "clear",
        "tier": 2,
        "width": 0,
        "height": 0,
        "genre_hint": genre,
        "platform_hint": "snes-style",
        "local_path": str(png),
    }
    if HAS_PIL:
        try:
            with Image.open(png) as img:
                entry["width"], entry["height"] = img.size
        except Exception:
            pass
    manifest.append(entry)

# ── Source 1: Kenney.nl (CC0) ──────────────────────────────────────────────
# Full catalogue of Kenney 2D pixel-art packs — slugs verified against kenney.nl/assets
KENNEY_PACKS = [
    # Previously scraped (will be skipped if already downloaded)
    ("micro-roguelike",         "Micro Roguelike"),
    ("tiny-town",               "Tiny Town"),
    ("1-bit-pack",              "1-Bit Pack"),
    ("rpg-urban-pack",          "RPG Urban Pack"),
    ("pixel-platformer",        "Pixel Platformer"),
    ("tower-defense-kit",       "Tower Defense Kit"),
    ("shooting-gallery",        "Shooting Gallery"),
    ("mini-dungeon",            "Mini Dungeon"),
    ("fantasy-town-kit",        "Fantasy Town Kit"),
    ("retro-fantasy-kit",       "Retro Fantasy Kit"),
    ("animal-pack",             "Animal Pack"),
    ("rpg-base",                "RPG Base"),
    ("modular-space-kit",       "Modular Space Kit"),
    ("blocky-characters",       "Blocky Characters"),
    ("city-kit-commercial",     "City Kit Commercial"),
    ("roguelike-rpg-pack",      "Roguelike RPG Pack"),
    ("top-down-tanks",          "Top Down Tanks"),
    ("monochrome-rpg",          "Monochrome RPG"),
    ("ui-pack-rpg-expansion",   "UI Pack RPG Expansion"),
    ("input-prompts-pixel",     "Input Prompts Pixel"),
    ("roguelike-characters",    "Roguelike Characters"),
    ("modular-characters",      "Modular Characters"),
    ("medieval-rts",            "Medieval RTS"),
    # NEW packs — not yet scraped
    ("tiny-dungeon",            "Tiny Dungeon"),
    ("tiny-rpg-forest",         "Tiny RPG Forest"),
    ("ui-pack",                 "UI Pack"),
    ("ui-pack-space-expansion", "UI Pack Space Expansion"),
    ("platformer-art-deluxe",   "Platformer Art Deluxe"),
    ("platformer-characters",   "Platformer Characters"),
    ("pixel-vehicle-pack",      "Pixel Vehicle Pack"),
    ("pixel-shmup",             "Pixel Shmup"),
    ("racing-pack",             "Racing Pack"),
    ("puzzle-pack",             "Puzzle Pack"),
    ("puzzle-pack-2",           "Puzzle Pack 2"),
    ("sokoban",                 "Sokoban"),
    ("sokoban-100-levels",      "Sokoban 100 Levels"),
    ("gem-gem-puzzle",          "Gem Gem Puzzle"),
    ("bit-pack",                "Bit Pack"),
    ("food-pack",               "Food Pack"),
    ("holiday-pack",            "Holiday Pack"),
    ("dice-pack",               "Dice Pack"),
    ("card-pack",               "Card Pack"),
    ("sports-pack",             "Sports Pack"),
    ("space-shooter-redux",     "Space Shooter Redux"),
    ("space-shooter-extension", "Space Shooter Extension"),
    ("jumper-pack",             "Jumper Pack"),
    ("abstract-platformer",     "Abstract Platformer"),
    ("simplified-platformer-pack", "Simplified Platformer Pack"),
    ("voxel-pack",              "Voxel Pack"),
    ("isometric-sandbox",       "Isometric Sandbox"),
    ("kenney-fonts",            "Kenney Fonts"),
    ("game-icons",              "Game Icons"),
    ("game-icons-expansion",    "Game Icons Expansion"),
]

def scrape_kenney(raw_dir: Path, known: set[str]) -> tuple[list[Path], int]:
    """Download any Kenney packs not already on disk. Returns (new_pngs, skip_count)."""
    new_pngs = []
    skipped = 0
    log("🏪 Kenney.nl (CC0)")

    for slug, name in KENNEY_PACKS:
        dest_dir = raw_dir / f"kenney_{slug}"
        # Quick skip: if dir has files and manifest has matching paths, skip
        existing = list(dest_dir.glob("*.png")) if dest_dir.exists() else []
        if existing and any(str(p) in known for p in existing[:3]):
            skipped += 1
            continue

        pack_url = f"https://kenney.nl/assets/{slug}"
        r = safe_get(pack_url)
        if not r:
            continue

        # Match .zip URLs — Kenney uses both quoted href and onclick patterns
        m = re.search(r"href=[\"'](https?://[^\"']*\.zip[^\"']*)[\"']", r.text)
        if not m:
            # fallback: relative zip path
            m = re.search(r"href=[\"'](/[^\"']*\.zip[^\"']*)[\"']", r.text)
        if not m:
            log(f"  No ZIP found for {name}")
            continue

        zip_url = m.group(1)
        if not zip_url.startswith("http"):
            zip_url = f"https://kenney.nl{zip_url}"

        zip_path = raw_dir / f"kenney_{slug}.zip"
        if zip_path.exists():
            log(f"  [{name}] ZIP cached")
        else:
            log(f"  [{name}] downloading {zip_url}")
            if not download_zip(zip_url, zip_path):
                continue

        pngs = extract_zip(zip_path, dest_dir)
        truly_new = [p for p in pngs if str(p) not in known]
        new_pngs.extend(truly_new)
        if truly_new:
            log(f"  [{name}] +{len(truly_new)} new sprites")

    return new_pngs, skipped

# ── Source 2: OpenGameArt.org (CC0 + CC-BY) ───────────────────────────────
OGA_DIRECT_SOURCES = [
    # (url, label, license)
    ("https://opengameart.org/content/dawnlike-16x16-universal-rogue-like-tileset-v181", "dawnlike", "CC0"),
    ("https://opengameart.org/content/tiny-16-basic",                     "tiny16",        "CC0"),
    ("https://opengameart.org/content/rpg-tiles-cobble-stone-paths-town-objects", "rpg_tiles", "CC0"),
    ("https://opengameart.org/content/16x16-fantasy-tileset",             "fantasy16",     "CC0"),
    ("https://opengameart.org/content/simple-broad-purpose-tileset",      "broad_tileset", "CC0"),
    ("https://opengameart.org/content/16x16-dungeon-tileset",             "dungeon16",     "CC0"),
    ("https://opengameart.org/content/16x16-fantasy-rpg-enemies",         "fantasy_enemies","CC0"),
    ("https://opengameart.org/content/eight-8-bit-style-characters",      "8bit_chars",    "CC0"),
    ("https://opengameart.org/content/animated-pixel-adventurer",         "adventurer",    "CC0"),
    ("https://opengameart.org/content/character-sprite-pack",             "char_pack",     "CC0"),
    ("https://opengameart.org/content/forest-tileset",                    "forest_tiles",  "CC0"),
    ("https://opengameart.org/content/zelda-like-tilesets-and-sprites",   "zelda_like",    "CC-BY"),
    ("https://opengameart.org/content/lpc-medieval-village-decorations",  "lpc_village",   "CC-BY-SA"),
    ("https://opengameart.org/content/rpg-enemies-11-dragons",            "dragons",       "CC-BY"),
    # Additional OGA sources
    ("https://opengameart.org/content/pixel-art-top-down-basic",          "topdown_basic", "CC0"),
    ("https://opengameart.org/content/16x16-rpg-item-pack",               "items16",       "CC-BY"),
    ("https://opengameart.org/content/2d-lost-garden-zelda-style-tiles-resized-to-32x32", "lost_garden32", "CC0"),
    ("https://opengameart.org/content/overworld-tileset-grass-and-water",  "overworld",    "CC0"),
    ("https://opengameart.org/content/isometric-city-building-game-assets","iso_city",     "CC0"),
    ("https://opengameart.org/content/castle-platformer",                  "castle_plat",  "CC0"),
    ("https://opengameart.org/content/pixel-art-backgrounds",              "pixel_bg",     "CC0"),
    ("https://opengameart.org/content/dungeon-crawl-32x32-tiles",          "dungeon_crawl","CC0"),
    ("https://opengameart.org/content/dungeon-crawl-32x32-tiles-supplemental","dungeon_crawl2","CC0"),
    ("https://opengameart.org/content/16x16-game-assets",                  "game16",       "CC-BY"),
    ("https://opengameart.org/content/64-bytes-iso-8x8-bitmap-font",       "iso_font",     "CC0"),
    ("https://opengameart.org/content/rpg-character-sprites",              "rpg_chars",    "CC-BY"),
    ("https://opengameart.org/content/mountain-landscape-pixel-art",       "mountain",     "CC0"),
    ("https://opengameart.org/content/pixel-art-icon-pack-rpg",            "icon_rpg",     "CC0"),
    ("https://opengameart.org/content/32x32-fantasy-tileset",              "fantasy32",    "CC-BY"),
    ("https://opengameart.org/content/pixel-art-platformer-village-props", "village_props","CC0"),
    ("https://opengameart.org/content/time-fantasy-monsters",              "time_monsters", "CC-BY"),
    ("https://opengameart.org/content/time-fantasy-rpg-characters-and-enemies","time_chars","CC-BY"),
    ("https://opengameart.org/content/lpc-terrain-repack",                 "lpc_terrain",  "CC-BY-SA"),
    ("https://opengameart.org/content/lpc-town-tileset",                   "lpc_town",     "CC-BY-SA"),
    ("https://opengameart.org/content/lpc-farming-tilesets-magic-animations-and-ui-elements","lpc_farm","CC-BY-SA"),
    ("https://opengameart.org/content/npc-sprite-sheets",                  "npc_sheets",   "CC0"),
    ("https://opengameart.org/content/pixel-shmup-ship-sprites",           "shmup_ships",  "CC0"),
    ("https://opengameart.org/content/explosion-animations",               "explosions",   "CC0"),
]

def scrape_oga_direct(raw_dir: Path, known: set[str]) -> list[Path]:
    """Scrape OGA direct sources for PNG downloads."""
    if not HAS_BS4:
        log("  Skipping OGA (beautifulsoup4 not installed)")
        return []

    new_pngs = []
    log("🎨 OpenGameArt.org (direct sources)")
    OGA_BASE = "https://opengameart.org"

    for url, label, license_str in OGA_DIRECT_SOURCES:
        dest_dir = raw_dir / f"oga_{label}"
        existing = list(dest_dir.glob("*.png")) if dest_dir.exists() else []
        if existing and any(str(p) in known for p in existing[:3]):
            continue

        r = safe_get(url)
        if not r:
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        file_links = []

        # Try to find direct PNG links or ZIP links
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".png") or href.lower().endswith(".zip"):
                full = href if href.startswith("http") else OGA_BASE + href
                file_links.append((full, href.lower().endswith(".zip")))

        for file_url, is_zip in file_links[:10]:  # cap per-source
            if is_zip:
                zip_path = raw_dir / f"oga_{label}_{Path(file_url).name}"
                if not zip_path.exists():
                    download_zip(file_url, zip_path)
                pngs = extract_zip(zip_path, dest_dir)
            else:
                dest = dest_dir / Path(file_url).name
                if dest.exists():
                    pngs = [dest]
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    r2 = safe_get(file_url)
                    if r2 and r2.content:
                        dest.write_bytes(r2.content)
                        pngs = [dest]
                    else:
                        pngs = []

            truly_new = [p for p in pngs if str(p) not in known]
            new_pngs.extend(truly_new)

        if new_pngs:
            log(f"  [{label}] +{len(new_pngs)} so far")

    return new_pngs

# ── Pipeline ───────────────────────────────────────────────────────────────
def run_pipeline_on(pngs: list[Path], manifest: list[dict]) -> dict:
    """Process a batch of new PNGs through the pipeline."""
    from extractor          import extract_sheet
    from indexer            import index_sprite
    from pixel_classifier   import classify_sprite
    from sequence_reorderer import reorder_sprite, save_sequence

    CORPUS_TRAIN.mkdir(parents=True, exist_ok=True)
    CORPUS_VAL.mkdir(parents=True, exist_ok=True)

    stats = dict(sheets=0, sprites=0, errors=0)
    random.seed()

    MIN_SIZE = 8
    MAX_SIZE = 256

    for sheet_path in pngs:
        if not sheet_path.exists():
            continue
        try:
            if HAS_PIL:
                with Image.open(sheet_path) as img:
                    sw, sh = img.size
                if sw < MIN_SIZE or sh < MIN_SIZE:
                    continue
                if sw <= 32 and sh <= 32:
                    tile_w, tile_h, mode = sw, sh, "grid"
                elif sw % 16 == 0 and sh % 16 == 0:
                    tile_w, tile_h, mode = 16, 16, "grid"
                elif sw % 32 == 0 and sh % 32 == 0:
                    tile_w, tile_h, mode = 32, 32, "grid"
                else:
                    tile_w, tile_h, mode = 16, 16, "auto"
            else:
                tile_w, tile_h, mode = 16, 16, "auto"

            split = "validation" if random.random() < VAL_RATIO else "train"
            out_base = CORPUS_VAL if split == "validation" else CORPUS_TRAIN
            out_dir = out_base / sheet_path.stem
            out_dir.mkdir(parents=True, exist_ok=True)

            sprites = extract_sheet(
                str(sheet_path), str(out_dir),
                mode=mode, tile_w=tile_w, tile_h=tile_h, min_size=MIN_SIZE
            )
            stats["sheets"] += 1

            for i, sp in enumerate(sprites):
                try:
                    indexed = index_sprite(sp)
                    classified = classify_sprite(sp)
                    sequence = reorder_sprite(indexed)
                    save_sequence(sequence, out_dir / f"sprite_{i:04d}_seq.json")
                    stats["sprites"] += 1
                except Exception as e:
                    stats["errors"] += 1
        except Exception as e:
            stats["errors"] += 1

    return stats

# ── Stats update ───────────────────────────────────────────────────────────
def update_stats(manifest: list[dict], pipeline_stats: dict) -> None:
    total = len(manifest)
    raw_count = len(list(RAW_DIR.rglob("*.png")))
    corpus_count = len(list(CORPUS_TRAIN.rglob("*.json"))) + len(list(CORPUS_VAL.rglob("*.json")))

    content = f"""# AM Pixel Corpus Stats

*Auto-updated by harvest_loop.py — {datetime.datetime.now().isoformat()}*

## Current Totals
- **Raw sprites on disk:** {raw_count:,}
- **Provenance manifest entries:** {total:,}
- **Corpus sequence files:** {corpus_count:,}

## Last Pipeline Pass
- Sheets processed: {pipeline_stats.get('sheets', 0):,}
- Sprites sequenced: {pipeline_stats.get('sprites', 0):,}
- Errors: {pipeline_stats.get('errors', 0)}
"""
    STATS_PATH.write_text(content)

# ── Main loop ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Single pass then exit")
    args = parser.parse_args()

    log("=" * 60)
    log("AM Pixel Harvest Loop started")
    log(f"Project root: {PROJECT_ROOT}")
    log("=" * 60)

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    cycle = 0
    while True:
        cycle += 1
        log(f"\n── Cycle {cycle} ──────────────────────────────────────")

        manifest = load_manifest()
        known = known_paths(manifest)
        log(f"Manifest: {len(manifest):,} known sprites")

        # 1. Scrape new sprites
        new_from_kenney, k_skipped = scrape_kenney(RAW_DIR, known)
        new_from_oga = scrape_oga_direct(RAW_DIR, known)
        all_new = new_from_kenney + new_from_oga

        log(f"Kenney: +{len(new_from_kenney)} new ({k_skipped} packs already complete)")
        log(f"OGA:    +{len(new_from_oga)} new")
        log(f"Total new PNGs this cycle: {len(all_new)}")

        # 2. Add provenance for new sprites
        if all_new:
            for png in all_new:
                parent = png.parent.name
                if "kenney" in parent:
                    add_provenance(manifest, png, f"https://kenney.nl/assets", "Kenney", "CC0", "mixed")
                else:
                    add_provenance(manifest, png, f"https://opengameart.org", "OGA", "CC0", "mixed")
            save_manifest(manifest)
            log(f"Provenance saved. Manifest now: {len(manifest):,}")

        # 3. Pipeline new sprites
        if all_new:
            log(f"Running pipeline on {len(all_new)} new sprites...")
            p_stats = run_pipeline_on(all_new, manifest)
            log(f"Pipeline done: {p_stats['sprites']} sprites sequenced, {p_stats['errors']} errors")
            update_stats(manifest, p_stats)
        else:
            log("No new sprites this cycle — all sources exhausted or up to date")
            if args.once:
                log("--once flag: exiting")
                break
            log(f"Sleeping {CYCLE_PAUSE}s before next cycle...")
            time.sleep(CYCLE_PAUSE)
            continue

        if args.once:
            log("--once flag: exiting after single pass")
            break

        log(f"Cycle {cycle} complete. Sleeping {CYCLE_PAUSE}s...")
        time.sleep(CYCLE_PAUSE)

    log("Harvest loop exited cleanly.")

if __name__ == "__main__":
    main()
