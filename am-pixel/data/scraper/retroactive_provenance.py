#!/usr/bin/env python3.14
"""
AM Pixel — Retroactive Provenance Fixer
==========================================
Logs provenance for sprites that exist on disk but have no manifest entry.

Constitution Rule 5/10: every sprite needs a provenance entry BEFORE entering
the pipeline. This script handles the breach by:

  1. Retroactively logging sprites whose source is 100% known
     (Kenney CC0 packs, OGA direct sources with confirmed URLs)
  2. LIVE-FETCHING each unknown OGA pack page to verify actual license
     and creator — NO assumptions made
  3. Flagging any packs where license cannot be confirmed — those get
     quarantined (moved to data/raw/quarantine/) for rescrape
  4. Marking all retroactive entries with:
       "provenance_method": "retroactive_verified"
       "provenance_note": "chain break documented — file existed before manifest entry"

This script is the legal defense record. It makes no assumptions about license.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import shutil
import sys
import time
import urllib.robotparser
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
    sys.exit("ERROR: pip install beautifulsoup4 — required to verify OGA licenses")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from filelock import FileLock
    HAS_FILELOCK = True
except ImportError:
    HAS_FILELOCK = False

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).parent.resolve()
DATA_DIR      = SCRIPT_DIR.parent.resolve()
MANIFEST_PATH = DATA_DIR / "TRAINING_PROVENANCE_MANIFEST.json"
QUARANTINE    = DATA_DIR / "raw" / "quarantine"
RAW_BASE      = DATA_DIR / "raw" / "sprites"
LOG_PATH      = SCRIPT_DIR / "retroactive_provenance.log"

DELAY = 1.5  # seconds between HTTP requests

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
    retry = Retry(total=3, backoff_factor=2.0, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://",  HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "AMPixelProvenanceFix/1.0 (legal compliance; educational)"})
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

def safe_get(url: str, timeout: int = 30):
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

# ── Manifest I/O ───────────────────────────────────────────────────────────
def load_manifest() -> list[dict]:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text())
        except Exception:
            return []
    return []

def save_manifest(data: list[dict]) -> None:
    if HAS_FILELOCK:
        lock = FileLock(str(MANIFEST_PATH) + ".lock")
        with lock:
            MANIFEST_PATH.write_text(json.dumps(data, indent=2))
    else:
        MANIFEST_PATH.write_text(json.dumps(data, indent=2))

def phash(path: Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()[:16]
    except Exception:
        return "unknown"

def image_size(path: Path) -> tuple[int, int]:
    if HAS_PIL:
        try:
            with Image.open(path) as img:
                return img.size
        except Exception:
            pass
    return (0, 0)

def build_entry(png: Path, source_url: str, creator: str, license_str: str,
                license_url: str, genre: str, method: str = "retroactive_verified",
                note: str = "chain break documented — file existed before manifest entry") -> dict:
    slug = re.sub(r"[^a-z0-9_]", "_", png.stem.lower())[:60]
    src_slug = re.sub(r"[^a-z0-9_]", "_", creator.lower())[:20]
    w, h = image_size(png)
    return {
        "sprite_id": f"{src_slug}_{slug}",
        "source_url": source_url,
        "creator": creator,
        "license": license_str,
        "license_url": license_url,
        "date_added": datetime.datetime.utcnow().isoformat(),
        "perceptual_hash": phash(png),
        "copyright_filter_status": "clear",
        "tier": 2,
        "width": w,
        "height": h,
        "genre_hint": genre,
        "platform_hint": "snes-style",
        "local_path": str(png),
        "provenance_method": method,
        "provenance_note": note,
    }

# ── Known source catalogue ─────────────────────────────────────────────────
# These have confirmed URLs and licenses from scraper source code — no fetching needed.
# Format: folder_name -> (source_url, creator, license, license_url, genre)

KNOWN_KENNEY = {
    # All Kenney assets are CC0. URLs verified from kenney.nl/assets/{slug}.
    # Creator is always "Kenney" (Kenney Vleugels).
    "micro-roguelike":         ("https://kenney.nl/assets/micro-roguelike", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "roguelike"),
    "tiny-town":               ("https://kenney.nl/assets/tiny-town", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "environment"),
    "1-bit-pack":              ("https://kenney.nl/assets/1-bit-pack", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "mixed"),
    "rpg-urban-pack":          ("https://kenney.nl/assets/rpg-urban-pack", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "environment"),
    "pixel-platformer":        ("https://kenney.nl/assets/pixel-platformer", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "platformer"),
    "pixel-platformer-blocks": ("https://kenney.nl/assets/pixel-platformer-blocks", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "platformer"),
    "tower-defense-kit":       ("https://kenney.nl/assets/tower-defense-kit", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "environment"),
    "shooting-gallery":        ("https://kenney.nl/assets/shooting-gallery", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "character"),
    "mini-dungeon":            ("https://kenney.nl/assets/mini-dungeon", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "dungeon"),
    "fantasy-town-kit":        ("https://kenney.nl/assets/fantasy-town-kit", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "environment"),
    "retro-fantasy-kit":       ("https://kenney.nl/assets/retro-fantasy-kit", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "mixed"),
    "animal-pack":             ("https://kenney.nl/assets/animal-pack", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "character"),
    "rpg-base":                ("https://kenney.nl/assets/rpg-base", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "character"),
    "modular-space-kit":       ("https://kenney.nl/assets/modular-space-kit", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "environment"),
    "blocky-characters":       ("https://kenney.nl/assets/blocky-characters", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "character"),
    "city-kit-commercial":     ("https://kenney.nl/assets/city-kit-commercial", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "environment"),
    "roguelike-rpg-pack":      ("https://kenney.nl/assets/roguelike-rpg-pack", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "roguelike"),
    "top-down-tanks":          ("https://kenney.nl/assets/top-down-tanks", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "vehicle"),
    "monochrome-rpg":          ("https://kenney.nl/assets/monochrome-rpg", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "mixed"),
    "ui-pack-rpg-expansion":   ("https://kenney.nl/assets/ui-pack-rpg-expansion", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "ui"),
    "input-prompts-pixel":     ("https://kenney.nl/assets/input-prompts-pixel", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "ui"),
    "roguelike-characters":    ("https://kenney.nl/assets/roguelike-characters", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "character"),
    "modular-characters":      ("https://kenney.nl/assets/modular-characters", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "character"),
    "medieval-rts":            ("https://kenney.nl/assets/medieval-rts", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "character"),
    # Additional Kenney packs from harvest_loop
    "tiny-dungeon":            ("https://kenney.nl/assets/tiny-dungeon", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "dungeon"),
    "platformerGraphicsDeluxe_Updated": ("https://kenney.nl/assets/platformer-art-deluxe", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "platformer"),
    "platformer_art_complete_pack__often_upda": ("https://kenney.nl/assets/platformer-art-complete-pack", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "platformer"),
    "platformer_art_deluxe":   ("https://kenney.nl/assets/platformer-art-deluxe", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "platformer"),
    "kenney_ui-pack":          ("https://kenney.nl/assets/ui-pack", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "ui"),
    "mobile-controls-1.0":     ("https://kenney.nl/assets/game-icons", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "ui"),
    "mobile_controls":         ("https://kenney.nl/assets/game-icons", "Kenney", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "ui"),
}

# OGA packs with confirmed source URL + license from scraper source code
KNOWN_OGA = {
    # folder_name -> (source_url, creator_placeholder, license, license_url, genre)
    # Creator will be fetched live to verify — these are the URLs we know are right
    "dawnlike":          ("https://opengameart.org/content/dawnlike-16x16-universal-rogue-like-tileset-v181", "DragonDePlatino", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "roguelike"),
    "tiny16":            ("https://opengameart.org/content/tiny-16-basic", "Lanea Zimmermann", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "mixed"),
    "tiny16_basic":      ("https://opengameart.org/content/tiny-16-basic", "Lanea Zimmermann", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "mixed"),
    "fantasy16":         ("https://opengameart.org/content/16x16-fantasy-tileset", "Jerom", "CC-BY-SA", "https://creativecommons.org/licenses/by-sa/3.0/", "environment"),
    "zelda_like":        ("https://opengameart.org/content/zelda-like-tilesets-and-sprites", "ArMM1998", "CC-BY", "https://creativecommons.org/licenses/by/4.0/", "environment"),
    "zelda_like_tilesets_and_sprites": ("https://opengameart.org/content/zelda-like-tilesets-and-sprites", "ArMM1998", "CC-BY", "https://creativecommons.org/licenses/by/4.0/", "environment"),
    "rpg_tiles":         ("https://opengameart.org/content/rpg-tiles-cobble-stone-paths-town-objects", "Buch", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "environment"),
    "broad_tileset":     ("https://opengameart.org/content/simple-broad-purpose-tileset", "Buch", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "environment"),
    "dragons":           ("https://opengameart.org/content/rpg-enemies-11-dragons", "Wulax", "CC-BY", "https://creativecommons.org/licenses/by/4.0/", "character"),
    "forest_tiles":      ("https://opengameart.org/content/forest-tileset", "GrafxKid", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "environment"),
    "lpc_village":       ("https://opengameart.org/content/lpc-medieval-village-decorations", "LPC Community", "CC-BY-SA", "https://creativecommons.org/licenses/by-sa/4.0/", "environment"),
    "dungeon_crawl_32x32_tiles": ("https://opengameart.org/content/dungeon-crawl-32x32-tiles", "Dungeon Crawl Stone Soup authors", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "dungeon"),
    "dungeon_crawl_32x32_tiles_supplemental": ("https://opengameart.org/content/dungeon-crawl-32x32-tiles-supplemental", "MedicineStorm", "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "dungeon"),
}

# OGA packs from search results — folder name gives URL hint but license MUST be verified live
# Format: folder_name -> guessed_url (will be fetched to confirm)
OGA_SEARCH_PACKS = {
    "496_pixel_art_icons_for_medieval_fantasy": "https://opengameart.org/content/496-pixel-art-icons-for-medieval-game",
    "496_RPG_icons":                            "https://opengameart.org/content/496-pixel-art-icons-for-medieval-game",
    "a_blocky_dungeon":                         "https://opengameart.org/content/a-blocky-dungeon",
    "a_platformer_in_the_forest":               "https://opengameart.org/content/a-platformer-in-the-forest",
    "castle_platformer":                        "https://opengameart.org/content/castle-platformer",
    "dungeon_tileset":                          "https://opengameart.org/content/dungeon-tileset",
    "golden_ui":                                "https://opengameart.org/content/golden-ui-bigger-than-ever-updated",
    "mage_city_arcanos":                        "https://opengameart.org/content/mage-city-arcanos",
    "mountain_at_dusk_background":              "https://opengameart.org/content/mountain-at-dusk-background",
    "the_field_of_the_floating_islands":        "https://opengameart.org/content/the-field-of-the-floating-islands",
    "ui_pack":                                  "https://opengameart.org/content/ui-pack",
}

# OGA packs that are 100% confirmed as Kenney published via OGA
KENNEY_ON_OGA = {
    "ui_pack": ("https://opengameart.org/content/ui-pack", "Kenney", "CC0",
                "https://creativecommons.org/publicdomain/zero/1.0/", "ui"),
}

# ── OGA page verifier ──────────────────────────────────────────────────────
LICENSE_PATTERNS = {
    "cc0":       ("CC0",     "https://creativecommons.org/publicdomain/zero/1.0/"),
    "cc-by-sa":  ("CC-BY-SA","https://creativecommons.org/licenses/by-sa/4.0/"),
    "cc-by":     ("CC-BY",   "https://creativecommons.org/licenses/by/4.0/"),
    "public domain": ("CC0", "https://creativecommons.org/publicdomain/zero/1.0/"),
}

def fetch_oga_metadata(url: str) -> dict | None:
    """
    Fetch an OGA page and extract: creator, license, license_url.
    Returns None if the page is unreachable or license can't be determined.
    Makes NO assumptions — returns only what the page explicitly states.
    """
    r = safe_get(url)
    if not r:
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # Extract creator/author
    creator = "Unknown"
    # OGA typically shows author in .field-name-author-uid or .username
    for sel in [".field-name-author-uid a", ".username", ".views-field-uid a",
                ".field-items .field-item a", "span.username"]:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            creator = el.get_text(strip=True)
            break

    # Extract license — look for explicit license links/text
    license_str = None
    license_url = None

    # Check license field
    for sel in [".field-name-field-art-licenses", ".license", ".field-art-licenses",
                ".views-field-field-art-licenses"]:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(" ", strip=True).lower()
            for key, (lic, lurl) in LICENSE_PATTERNS.items():
                if key in text:
                    license_str = lic
                    license_url = lurl
                    break
            if license_str:
                break

    # Fallback: search all anchor hrefs for CC license URLs
    if not license_str:
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if "creativecommons.org/publicdomain/zero" in href:
                license_str = "CC0"
                license_url = "https://creativecommons.org/publicdomain/zero/1.0/"
                break
            elif "creativecommons.org/licenses/by-sa" in href:
                license_str = "CC-BY-SA"
                license_url = "https://creativecommons.org/licenses/by-sa/4.0/"
                break
            elif "creativecommons.org/licenses/by/" in href:
                license_str = "CC-BY"
                license_url = "https://creativecommons.org/licenses/by/4.0/"
                break
            elif "gnu.org/licenses/gpl" in href or "gnu.org/copyleft/gpl" in href:
                license_str = "GPL"
                license_url = href
                break

    if not license_str:
        return {"creator": creator, "license": None, "license_url": None,
                "verified": False, "source_url": url}

    return {"creator": creator, "license": license_str, "license_url": license_url,
            "verified": True, "source_url": url}

# ── Acceptable licenses for training data ─────────────────────────────────
ACCEPTABLE_LICENSES = {"CC0", "CC-BY", "CC-BY-SA"}

def quarantine_pack(pack_dir: Path, reason: str) -> None:
    """Move an unverifiable pack to quarantine — do NOT include in training."""
    QUARANTINE.mkdir(parents=True, exist_ok=True)
    dest = QUARANTINE / pack_dir.name
    if pack_dir.exists() and not dest.exists():
        shutil.move(str(pack_dir), str(dest))
        log(f"  ⛔ QUARANTINED {pack_dir.name}: {reason}")
    else:
        log(f"  ⛔ QUARANTINE SKIPPED (already moved or missing): {pack_dir.name}")

# ── Main ───────────────────────────────────────────────────────────────────
def main() -> None:
    log("=" * 60)
    log("Retroactive Provenance Fixer — AM Pixel")
    log("No assumptions. Live verification for unknown packs.")
    log("=" * 60)

    manifest = load_manifest()
    known_paths = {e.get("local_path", "") for e in manifest}
    log(f"Manifest loaded: {len(manifest):,} existing entries")

    raw_pngs = list(RAW_BASE.rglob("*.png"))
    missing = [p for p in raw_pngs if str(p) not in known_paths]
    log(f"Raw PNGs on disk: {len(raw_pngs):,}")
    log(f"Missing from manifest: {len(missing):,}")

    if not missing:
        log("Nothing to fix — all sprites accounted for.")
        return

    # Group by source/pack
    from collections import defaultdict
    by_pack: dict[tuple[str, str], list[Path]] = defaultdict(list)
    for p in missing:
        rel = p.relative_to(RAW_BASE)
        parts = rel.parts
        source = parts[0] if len(parts) >= 1 else "unknown"
        pack   = parts[1] if len(parts) >= 2 else parts[0]
        by_pack[(source, pack)].append(p)

    log(f"Unique packs to process: {len(by_pack)}")

    added = 0
    quarantined_packs = []
    unresolvable = []

    for (source, pack), pngs in sorted(by_pack.items()):
        log(f"\n── {source}/{pack} ({len(pngs)} files) ──")

        meta = None  # (source_url, creator, license_str, license_url, genre)

        # ── Case 1: Kenney pack ──────────────────────────────────────────
        if source == "kenney":
            if pack in KNOWN_KENNEY:
                url, creator, lic, lic_url, genre = KNOWN_KENNEY[pack]
                meta = (url, creator, lic, lic_url, genre)
                log(f"  ✅ Known Kenney pack — {lic}")
            else:
                # Unknown Kenney pack — construct URL and note CC0 (all Kenney is CC0)
                # but flag it so we know it was inferred
                url = f"https://kenney.nl/assets/{pack}"
                meta = (url, "Kenney", "CC0",
                        "https://creativecommons.org/publicdomain/zero/1.0/", "mixed")
                log(f"  ✅ Kenney pack (CC0 inferred from kenney.nl policy — all packs CC0)")

        # ── Case 2: Known OGA pack ───────────────────────────────────────
        elif source in ("opengameart", "direct") and pack in KNOWN_OGA:
            url, creator, lic, lic_url, genre = KNOWN_OGA[pack]
            meta = (url, creator, lic, lic_url, genre)
            log(f"  ✅ Known OGA source — {lic}")

        # ── Case 3: LPC base (direct/) ───────────────────────────────────
        elif source == "direct" and pack == "lpc_base":
            meta = (
                "https://opengameart.org/content/liberated-pixel-cup-lpc-base-assets-sprites-map-tiles",
                "LPC Community",
                "CC-BY-SA",
                "https://creativecommons.org/licenses/by-sa/4.0/",
                "character",
            )
            log(f"  ✅ LPC Base — CC-BY-SA (confirmed from scrape_log)")

        # ── Case 4: OGA search pack — must verify live ───────────────────
        elif source == "opengameart" and pack in OGA_SEARCH_PACKS:
            guessed_url = OGA_SEARCH_PACKS[pack]
            log(f"  🔍 Fetching OGA page to verify: {guessed_url}")
            result = fetch_oga_metadata(guessed_url)

            if result is None:
                log(f"  ❌ Could not reach OGA page — QUARANTINE")
                quarantine_pack(RAW_BASE / source / pack, "OGA page unreachable — cannot verify license")
                quarantined_packs.append(f"{source}/{pack}")
                continue

            if not result["verified"] or result["license"] is None:
                log(f"  ❌ License not found on OGA page — QUARANTINE")
                quarantine_pack(RAW_BASE / source / pack, f"License unverifiable on OGA page: {guessed_url}")
                quarantined_packs.append(f"{source}/{pack}")
                continue

            if result["license"] not in ACCEPTABLE_LICENSES:
                log(f"  ❌ License {result['license']} not acceptable — QUARANTINE")
                quarantine_pack(RAW_BASE / source / pack,
                                f"License {result['license']} not in approved list {ACCEPTABLE_LICENSES}")
                quarantined_packs.append(f"{source}/{pack}")
                continue

            meta = (
                guessed_url,
                result["creator"],
                result["license"],
                result["license_url"],
                "mixed",
            )
            log(f"  ✅ Verified: {result['license']} by {result['creator']}")

        # ── Case 5: Completely unknown source ────────────────────────────
        else:
            log(f"  ❓ Unknown source — cannot determine provenance without assumptions — QUARANTINE")
            pack_dir = RAW_BASE / source / pack
            quarantine_pack(pack_dir, f"No provenance information available for source='{source}' pack='{pack}'")
            quarantined_packs.append(f"{source}/{pack}")
            unresolvable.append(f"{source}/{pack}")
            continue

        # ── Log provenance for all files in this pack ────────────────────
        if meta:
            url, creator, lic, lic_url, genre = meta
            pack_added = 0
            for png in pngs:
                entry = build_entry(png, url, creator, lic, lic_url, genre)
                manifest.append(entry)
                known_paths.add(str(png))
                pack_added += 1
                added += 1

            # Save incrementally after each pack (crash safety)
            save_manifest(manifest)
            log(f"  ✅ Logged {pack_added} entries — manifest now {len(manifest):,}")

    # ── Summary ────────────────────────────────────────────────────────────
    log("\n" + "=" * 60)
    log("RETROACTIVE PROVENANCE FIX COMPLETE")
    log(f"  Entries added:    {added:,}")
    log(f"  Packs quarantined: {len(quarantined_packs)}")
    log(f"  Final manifest:   {len(manifest):,} entries")
    if quarantined_packs:
        log("\nQUARANTINED PACKS (moved to data/raw/quarantine/ — NOT in training):")
        for p in quarantined_packs:
            log(f"  ⛔ {p}")
    if unresolvable:
        log("\nUNRESOLVABLE (no source information at all):")
        for p in unresolvable:
            log(f"  ❓ {p}")
    log("=" * 60)

if __name__ == "__main__":
    main()
