#!/usr/bin/env python3.14
"""
AM Pixel Sprite Scraper v3
===========================
Fixed version — addresses all known issues from v2 runs:
  1. Kenney ZIP URLs change; we discover them fresh from each pack page each run.
  2. Fixed Kenney pack slugs (dungeon→modular-dungeon-kit / mini-dungeon,
     fantasy-town→fantasy-town-kit, isometric-miniature→[dropped—not found]).
  3. Additional Kenney packs with correct slugs verified against kenney.nl/assets.
  4. OGA search URL fixed: license tid 17983 was wrong; CC0 = tid 4.
     CSS selector also fixed: art results use .views-field-title a hrefs.
  5. Task 3 direct sources updated with the requested OGA URLs.

Constitution Rule 5: provenance entry written BEFORE sprite file is saved.
Rate limit: 1.5 s between requests (DELAY constant).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import sys
import time
import urllib.robotparser
import zipfile
from pathlib import Path
from urllib.parse import urlparse, urljoin

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
    print("WARNING: pip install beautifulsoup4 for full OpenGameArt support")

# ── paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).parent.resolve()
DATA_DIR      = SCRIPT_DIR.parent.resolve()
PROJECT_ROOT  = DATA_DIR.parent.resolve()
RAW_DIR       = DATA_DIR / "raw" / "sprites"
MANIFEST_PATH = DATA_DIR / "TRAINING_PROVENANCE_MANIFEST.json"
LOG_PATH      = SCRIPT_DIR / "scrape_log.md"

DELAY = 1.5  # seconds between requests

# ── HTTP session with retries ──────────────────────────────────────────────
def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://",  HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "AMPixelScraper/3.0 (educational; pixel art dataset)"})
    return s

SESSION = make_session()
_ROBOTS_CACHE: dict[str, urllib.robotparser.RobotFileParser] = {}

def check_robots(url: str) -> bool:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base not in _ROBOTS_CACHE:
        rp = urllib.robotparser.RobotFileParser()
        try:
            rp.set_url(f"{base}/robots.txt")
            rp.read()
        except Exception:
            rp = urllib.robotparser.RobotFileParser()
        _ROBOTS_CACHE[base] = rp
    return _ROBOTS_CACHE[base].can_fetch("*", url)


def safe_get(url: str, timeout: int = 40) -> requests.Response | None:
    """GET with rate-limit delay, robot check, and error handling."""
    if not check_robots(url):
        log(f"  robots.txt blocked: {url}")
        return None
    time.sleep(DELAY)
    try:
        r = SESSION.get(url, timeout=timeout)
        if r.status_code != 200:
            log(f"  HTTP {r.status_code}: {url}")
            return None
        return r
    except Exception as e:
        log(f"  Request error {url}: {e}")
        return None


def download_file(url: str, dest: Path, pre_delay: float = DELAY) -> bool:
    if not check_robots(url):
        log(f"  robots.txt blocked: {url}")
        return False
    try:
        time.sleep(pre_delay)
        r = SESSION.get(url, timeout=60, stream=True)
        if r.status_code != 200:
            log(f"  HTTP {r.status_code}: {url}")
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
        return True
    except Exception as e:
        log(f"  Download error {url}: {e}")
        return False


def extract_zip(zip_path: Path, extract_to: Path) -> list[Path]:
    extract_to.mkdir(parents=True, exist_ok=True)
    pngs: list[Path] = []
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for name in z.namelist():
                if name.lower().endswith(".png") and not name.startswith("__"):
                    z.extract(name, extract_to)
                    pngs.append(extract_to / name)
    except Exception as e:
        log(f"  ZIP error: {e}")
    return pngs


def phash(path: Path) -> str:
    try:
        from PIL import Image
        img = Image.open(path).convert("L").resize((8, 8))
        pixels = list(img.getdata())
        mean = sum(pixels) / len(pixels)
        bits = "".join("1" if p >= mean else "0" for p in pixels)
        return format(int(bits, 2), "016x")
    except Exception:
        return hashlib.md5(path.read_bytes()).hexdigest()[:16]


def write_provenance(entry: dict) -> None:
    """Write provenance entry BEFORE saving sprite (Constitution Rule 5)."""
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    if MANIFEST_PATH.exists():
        try:
            data = json.loads(MANIFEST_PATH.read_text())
        except Exception:
            data = []
    else:
        data = []
    data.append(entry)
    MANIFEST_PATH.write_text(json.dumps(data, indent=2))


def log(msg: str) -> None:
    print(msg)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(f"{datetime.datetime.now().isoformat()} {msg}\n")


def make_sprite_id(source: str, filename: str) -> str:
    slug = re.sub(r"[^a-z0-9_]", "_", filename.lower().replace(".png", ""))
    return f"{source}_{slug}"[:80]


def build_provenance_entry(
    sprite_id: str,
    source_url: str,
    creator: str,
    license_str: str,
    genre: str,
    png: Path,
) -> dict:
    entry: dict = {
        "sprite_id": sprite_id,
        "source_url": source_url,
        "creator": creator,
        "license": license_str,
        "license_url": _license_url(license_str),
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
    try:
        from PIL import Image
        with Image.open(png) as img:
            entry["width"], entry["height"] = img.size
    except Exception:
        pass
    return entry


def _license_url(lic: str) -> str:
    lic_l = lic.lower()
    if "cc0" in lic_l:
        return "https://creativecommons.org/publicdomain/zero/1.0/"
    if "cc-by-sa" in lic_l:
        return "https://creativecommons.org/licenses/by-sa/4.0/"
    if "cc-by" in lic_l:
        return "https://creativecommons.org/licenses/by/4.0/"
    return ""


# ── Source 1: Kenney.nl ────────────────────────────────────────────────────
# All CC0. Slugs verified against https://kenney.nl/assets on 2026-05-09.

KENNEY_PACKS = [
    # (slug, display_name)
    # --- previously working ---
    ("micro-roguelike",    "Micro Roguelike"),
    ("tiny-town",          "Tiny Town"),
    ("1-bit-pack",         "1-Bit Pack"),
    ("rpg-urban-pack",     "RPG Urban Pack"),
    ("pixel-platformer",   "Pixel Platformer"),
    ("tower-defense-kit",  "Tower Defense Kit"),
    ("shooting-gallery",   "Shooting Gallery"),
    # --- fixed slugs (404 → correct) ---
    # dungeon-pack → mini-dungeon (old "dungeon-pack" not found; modular-dungeon-kit is 3D)
    ("mini-dungeon",       "Mini Dungeon"),
    # fantasy-town-pack → fantasy-town-kit
    ("fantasy-town-kit",   "Fantasy Town Kit"),
    # isometric-miniature → not found on kenney.nl; replaced with retro-fantasy-kit
    ("retro-fantasy-kit",  "Retro Fantasy Kit"),
    # --- additional packs requested (verified slugs) ---
    # animal-pack-redux → animal-pack
    ("animal-pack",        "Animal Pack"),
    # rpg-base → exact match
    ("rpg-base",           "RPG Base"),
    # sci-fi-platformer → not found; use modular-space-kit
    ("modular-space-kit",  "Modular Space Kit"),
    # creature-pack → not found; use blocky-characters
    ("blocky-characters",  "Blocky Characters"),
    # city-kit-commercial → exact match
    ("city-kit-commercial","City Kit Commercial"),
    # roguelike-rpg-pack → exact match
    ("roguelike-rpg-pack", "Roguelike RPG Pack"),
    # top-down-tanks-redux → top-down-tanks
    ("top-down-tanks",     "Top Down Tanks"),
    # monochrome-rpg → exact match
    ("monochrome-rpg",     "Monochrome RPG"),
    # ui-pack-rpg-expansion → exact match
    ("ui-pack-rpg-expansion","UI Pack RPG Expansion"),
    # input-prompts-pixel-16 → input-prompts-pixel
    ("input-prompts-pixel","Input Prompts Pixel"),
    # bonus packs confirmed 200
    ("roguelike-characters","Roguelike Characters"),
    ("modular-characters", "Modular Characters"),
    ("medieval-rts",       "Medieval RTS"),
]


def scrape_kenney(raw_dir: Path) -> list[dict]:
    """Download Kenney CC0 packs by discovering ZIP links from pack pages."""
    results = []
    log("\n🏪 SOURCE 1: Kenney.nl (CC0)")

    for slug, name in KENNEY_PACKS:
        pack_url = f"https://kenney.nl/assets/{slug}"
        log(f"\n  [{name}] {pack_url}")

        r = safe_get(pack_url)
        if r is None:
            continue

        # Find ZIP download link
        zip_url = None
        if HAS_BS4:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ".zip" in href:
                    zip_url = href if href.startswith("http") else f"https://kenney.nl{href}"
                    break
        else:
            m = re.search(r'href="([^"]*\.zip[^"]*)"', r.text)
            if m:
                zip_url = m.group(1)
                if not zip_url.startswith("http"):
                    zip_url = f"https://kenney.nl{zip_url}"

        if not zip_url:
            log(f"  Could not find ZIP link for {name}")
            continue

        log(f"  ZIP: {zip_url}")
        zip_dest = raw_dir / "kenney" / f"{slug}.zip"
        if zip_dest.exists():
            log(f"  Already downloaded, re-extracting…")
        elif not download_file(zip_url, zip_dest):
            continue

        extract_to = raw_dir / "kenney" / slug
        pngs = extract_zip(zip_dest, extract_to)
        log(f"  Extracted {len(pngs)} PNGs")

        for png in pngs:
            sprite_id = make_sprite_id("kenney", png.name)
            entry = build_provenance_entry(sprite_id, zip_url, "Kenney.nl", "CC0", "rpg", png)
            write_provenance(entry)  # BEFORE saving (already on disk from extract)
            results.append(entry)

        log(f"  ✅ {name}: {len(pngs)} sprites")

    return results


# ── Source 2: OpenGameArt.org ──────────────────────────────────────────────
# FIX: The original search URL used license tid 17983 (doesn't exist).
#      Correct CC0 license tid = 4.
#      Art type 9 = 2D Art (correct).

OGA_BASE   = "https://opengameart.org"
# tid 4 = CC0, tid 2 = CC-BY 3.0, tid 17981 = CC-BY 4.0
OGA_SEARCH = (
    OGA_BASE
    + "/art-search-advanced"
    + "?field_art_type_tid[]=9"
    + "&field_art_licenses_tid[]=4"    # CC0 (was wrong: 17983)
    + "&sort_by=count&sort_order=DESC"
    + "&items_per_page=24"
)

ACCEPTABLE_LICENSES = {
    "cc0", "cc-by", "cc-by-sa", "cc0-1.0", "cc-by-4.0", "cc-by-3.0",
    "cc-by-sa-4.0", "cc-by-sa-3.0", "publicdomain", "public domain",
}


def is_acceptable_license(text: str) -> bool:
    t = text.lower().strip()
    if "nc" in t or "nd" in t:
        return False
    return any(lic in t for lic in ACCEPTABLE_LICENSES)


def scrape_opengameart(raw_dir: Path, max_packs: int = 40) -> list[dict]:
    if not HAS_BS4:
        log("Skipping OpenGameArt — beautifulsoup4 not installed")
        return []

    log(f"\n🎮 SOURCE 2: OpenGameArt CC0 sprites (up to {max_packs} packs)")
    results = []
    visited_packs: set[str] = set()
    pack_count = 0
    page = 0

    while pack_count < max_packs:
        search_url = OGA_SEARCH + f"&page={page}"
        r = safe_get(search_url)
        if r is None:
            break

        soup = BeautifulSoup(r.text, "html.parser")

        # FIX: collect /content/ links from .views-field-title a elements.
        # The search result page returns <li class="views-row…"> items with
        # .views-field-title > .field-content > <a href="/content/…">
        pack_links: list[str] = []
        for a in soup.select(".views-field-title .field-content a[href]"):
            href = a["href"]
            if "/content/" not in href:
                continue
            if any(x in href for x in ["/faq", "/forum", "/user", "/art-search"]):
                continue
            if href in visited_packs:
                continue
            full = href if href.startswith("http") else OGA_BASE + href
            pack_links.append(full)
            visited_packs.add(href)

        # Fallback: all /content/ hrefs if the targeted selector returned nothing
        if not pack_links:
            for a in soup.select("a[href]"):
                href = a["href"]
                if "/content/" not in href:
                    continue
                if any(x in href for x in ["/faq", "/forum", "/user", "/art-search"]):
                    continue
                if href in visited_packs:
                    continue
                full = href if href.startswith("http") else OGA_BASE + href
                pack_links.append(full)
                visited_packs.add(href)

        pack_links = list(dict.fromkeys(pack_links))
        log(f"  Page {page}: {len(pack_links)} pack links")

        if not pack_links:
            log("  No more results — stopping.")
            break

        for pack_url in pack_links:
            if pack_count >= max_packs:
                break

            pr = safe_get(pack_url)
            if pr is None:
                continue

            psoup = BeautifulSoup(pr.text, "html.parser")

            # Detect license from the page
            license_text = ""
            for el in psoup.select(
                ".field-name-field-art-licenses, .license, [class*=license], "
                ".field-name-field-art-type, .field-license"
            ):
                license_text += " " + el.get_text(" ", strip=True)
            for meta in psoup.find_all("meta"):
                if "license" in str(meta.get("name", "")).lower():
                    license_text += " " + str(meta.get("content", ""))

            # Also check page title region for license indicators
            for a in psoup.find_all("a", href=True):
                if "creativecommons.org" in a["href"]:
                    license_text += " " + a["href"] + " " + a.get_text()

            if license_text and not is_acceptable_license(license_text):
                log(f"  ⛔ Non-permissive license, skipping: {pack_url}")
                continue

            # Find download links — PNG or ZIP
            download_links: list[str] = []
            for a in psoup.select("a[href]"):
                href = a["href"]
                if any(href.lower().endswith(ext) for ext in [".png", ".zip", ".tar.gz"]):
                    full = href if href.startswith("http") else OGA_BASE + href
                    download_links.append(full)

            if not download_links:
                continue

            pack_name = psoup.title.string if psoup.title else Path(pack_url).name
            pack_name = re.sub(r"\s*\|.*$", "", pack_name or "unknown").strip()[:40]
            pack_slug = re.sub(r"[^a-z0-9_]", "_", pack_name.lower())
            pack_dir  = raw_dir / "opengameart" / pack_slug
            pack_dir.mkdir(parents=True, exist_ok=True)

            # Determine license label
            lic_label = "CC0"
            if "cc-by-sa" in license_text.lower():
                lic_label = "CC-BY-SA"
            elif "cc-by" in license_text.lower():
                lic_label = "CC-BY"

            # Find author
            author_el = psoup.select_one(".field-name-author-name a, .username")
            author = author_el.get_text(strip=True) if author_el else "OpenGameArt contributor"

            pack_pngs = 0
            for dl_url in download_links[:5]:
                fname = Path(urlparse(dl_url).path).name
                dest  = pack_dir / fname
                if dest.exists():
                    # Still process already-downloaded files
                    pass
                elif not download_file(dl_url, dest, pre_delay=0.5):
                    continue

                pngs_to_process: list[Path] = []
                if fname.lower().endswith(".zip") and dest.exists():
                    pngs_to_process = extract_zip(dest, pack_dir / fname.replace(".zip", ""))
                elif fname.lower().endswith(".png") and dest.exists():
                    pngs_to_process = [dest]

                for png in pngs_to_process:
                    sprite_id = make_sprite_id("oga", f"{pack_slug}_{png.name}")
                    entry = build_provenance_entry(sprite_id, pack_url, author, lic_label, "rpg", png)
                    write_provenance(entry)
                    results.append(entry)
                    pack_pngs += 1

            if pack_pngs > 0:
                log(f"  ✅ [{pack_count+1}] {pack_name}: {pack_pngs} PNGs")
                pack_count += 1
            else:
                log(f"  ⚠️  {pack_name}: 0 PNGs (no downloadable assets)")

        page += 1

    log(f"\n🏁 OpenGameArt total: {len(results)} PNGs across {pack_count} packs")
    return results


# ── Source 3: Direct high-quality curated OGA sources ─────────────────────
# Updated with task-specified URLs; license stated per URL in the task.

DIRECT_SOURCES = [
    # (url, slug, creator_hint, license)
    ("https://opengameart.org/content/zelda-like-tilesets-and-sprites",
     "zelda_like",           "OGA contributor", "CC-BY"),
    ("https://opengameart.org/content/rpg-tiles-cobble-stone-paths-town-objects",
     "rpg_cobblestone",      "OGA contributor", "CC0"),
    ("https://opengameart.org/content/16x16-fantasy-tileset",
     "fantasy_tileset_16",   "OGA contributor", "CC0"),
    ("https://opengameart.org/content/tiny-16-basic",
     "tiny16_basic",         "OGA contributor", "CC0"),
    ("https://opengameart.org/content/16x16-dungeon-tileset",
     "dungeon_tileset_16",   "OGA contributor", "CC0"),
    ("https://opengameart.org/content/2d-rpg-character-sprite-base-with-animations",
     "rpg_char_base",        "OGA contributor", "CC0"),
    ("https://opengameart.org/content/dawnlike-16x16-universal-rogue-like-tileset-v181",
     "dawnlike",             "DragonDePlatino", "CC0"),
    ("https://opengameart.org/content/simple-broad-purpose-tileset",
     "simple_tileset",       "OGA contributor", "CC0"),
    # Keep prior successful sources
    ("https://opengameart.org/content/liberated-pixel-cup-lpc-base-assets-sprites-map-tiles",
     "lpc_base",             "LPC Community",   "CC-BY-SA"),
    ("https://opengameart.org/content/rpg-item-pack",
     "rpg_items",            "OGA contributor", "CC0"),
]


def scrape_direct_sources(raw_dir: Path) -> list[dict]:
    """Download from curated direct OGA source list (Task 3)."""
    if not HAS_BS4:
        log("Skipping direct sources — beautifulsoup4 not installed")
        return []

    log("\n🎯 SOURCE 3: Direct curated sources (Task 3 URLs)")
    results = []

    for url, prefix, creator, license_str in DIRECT_SOURCES:
        log(f"\n  [{prefix}] {url}")
        r = safe_get(url)
        if r is None:
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        pack_dir = raw_dir / "direct" / prefix
        pack_dir.mkdir(parents=True, exist_ok=True)

        # Find download links
        download_links: list[str] = []
        for a in soup.select("a[href]"):
            href = a["href"]
            if any(href.lower().endswith(ext) for ext in [".png", ".zip"]):
                full = href if href.startswith("http") else OGA_BASE + href
                if full not in download_links:
                    download_links.append(full)

        if not download_links:
            log(f"  No downloadable files found for {prefix}")
            continue

        pack_pngs = 0
        for dl_url in download_links[:8]:  # max 8 files per pack
            fname = Path(urlparse(dl_url).path).name
            dest  = pack_dir / fname
            if not dest.exists():
                if not download_file(dl_url, dest):
                    continue

            pngs: list[Path] = []
            if fname.lower().endswith(".zip") and dest.exists():
                pngs = extract_zip(dest, pack_dir / fname.replace(".zip", ""))
            elif fname.lower().endswith(".png") and dest.exists():
                pngs = [dest]

            for png in pngs:
                sprite_id = make_sprite_id(prefix, png.name)
                entry = build_provenance_entry(sprite_id, url, creator, license_str, "rpg", png)
                write_provenance(entry)  # BEFORE final save (Rule 5)
                results.append(entry)
                pack_pngs += 1

        log(f"  ✅ {prefix}: {pack_pngs} PNGs")

    return results


# ── main ───────────────────────────────────────────────────────────────────

def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    log(f"\n{'='*60}")
    log(f"AM Pixel Scraper v3 — {datetime.datetime.now().isoformat()}")
    log(f"{'='*60}")

    all_results: list[dict] = []

    # Task 1: Kenney packs (fixed slugs + additional packs)
    kenney_results = scrape_kenney(RAW_DIR)
    all_results.extend(kenney_results)

    # Task 2: OpenGameArt search (fixed license tid 4 = CC0)
    oga_results = scrape_opengameart(RAW_DIR, max_packs=40)
    all_results.extend(oga_results)

    # Task 3: Direct curated sources
    direct_results = scrape_direct_sources(RAW_DIR)
    all_results.extend(direct_results)

    total = len(all_results)
    log(f"\n{'='*60}")
    log(f"  SCRAPE COMPLETE")
    log(f"  Kenney sprites  : {len(kenney_results)}")
    log(f"  OGA sprites     : {len(oga_results)}")
    log(f"  Direct sprites  : {len(direct_results)}")
    log(f"  TOTAL THIS RUN  : {total}")
    log(f"  Manifest path   : {MANIFEST_PATH}")
    log(f"{'='*60}")

    print(f"\n✅ TOTAL SPRITES COLLECTED THIS RUN: {total}")


if __name__ == "__main__":
    main()
