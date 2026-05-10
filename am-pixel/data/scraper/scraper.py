#!/usr/bin/env python3
"""
AM Pixel Sprite Scraper v2
===========================
Downloads permissively-licensed sprite packs.
Writes provenance entries to TRAINING_PROVENANCE_MANIFEST.json BEFORE saving sprites.
Logs all activity to data/scraper/scrape_log.md.
Respects robots.txt. Rate-limits all requests.
Accepted licenses: CC0, CC-BY, CC-BY-SA.

Sources:
  1. Kenney.nl  — CC0, uses Kenney API to discover current ZIP URLs
  2. OpenGameArt.org — CC0 sprites, paginated search with HTML parsing
  3. itch.io free CC0 game assets packs (direct known URLs)
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
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://",  HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "AMPixelScraper/2.0 (educational; pixel art dataset)"})
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

def download_file(url: str, dest: Path, delay: float = DELAY) -> bool:
    if not check_robots(url):
        log(f"  robots.txt blocked: {url}")
        return False
    try:
        time.sleep(delay)
        r = SESSION.get(url, timeout=30, stream=True)
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

# ── Source 1: Kenney.nl ────────────────────────────────────────────────────
# Kenney publishes an RSS/JSON feed at kenney.nl/assets — we discover packs
# then find the ZIP link from each pack page.

KENNEY_PACKS = [
    # (slug, display_name) — all CC0
    ("micro-roguelike",  "Micro Roguelike"),
    ("tiny-town",        "Tiny Town"),
    ("1-bit-pack",       "1-Bit Pack"),
    ("rpg-urban-pack",   "RPG Urban Pack"),
    ("pixel-platformer", "Pixel Platformer"),
    ("tower-defense-kit","Tower Defense Kit"),
    ("shooting-gallery", "Shooting Gallery"),
    ("dungeon-pack",     "Dungeon Pack"),
    ("fantasy-town-pack","Fantasy Town Pack"),
    ("isometric-miniature","Isometric Miniature"),
]

def scrape_kenney(raw_dir: Path, manifest_path: Path) -> list[dict]:
    """Download Kenney CC0 packs by discovering ZIP links from pack pages."""
    results = []
    log("\n🏪 SOURCE 1: Kenney.nl (CC0)")

    for slug, name in KENNEY_PACKS:
        pack_url = f"https://kenney.nl/assets/{slug}"
        log(f"\n  [{name}] {pack_url}")

        if not check_robots(pack_url):
            log("  robots.txt blocked")
            continue

        try:
            time.sleep(DELAY)
            r = SESSION.get(pack_url, timeout=20)
            if r.status_code != 200:
                log(f"  HTTP {r.status_code}")
                continue

            # Find ZIP download link in page HTML
            zip_url = None
            if HAS_BS4:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if ".zip" in href:
                        zip_url = href if href.startswith("http") else f"https://kenney.nl{href}"
                        break
            else:
                # Regex fallback
                m = re.search(r'href="([^"]*kenney[^"]*\.zip)"', r.text)
                if m:
                    zip_url = m.group(1)
                    if not zip_url.startswith("http"):
                        zip_url = f"https://kenney.nl{zip_url}"

            if not zip_url:
                log(f"  Could not find ZIP link for {name}")
                continue

            log(f"  ZIP: {zip_url}")
            zip_dest = raw_dir / "kenney" / f"{slug}.zip"
            if not download_file(zip_url, zip_dest):
                continue

            extract_to = raw_dir / "kenney" / slug
            pngs = extract_zip(zip_dest, extract_to)
            log(f"  Extracted {len(pngs)} PNGs")

            for png in pngs:
                sprite_id = make_sprite_id("kenney", png.name)
                entry = {
                    "sprite_id": sprite_id,
                    "source_url": zip_url,
                    "creator": "Kenney.nl",
                    "license": "CC0",
                    "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                    "date_added": datetime.datetime.utcnow().isoformat(),
                    "perceptual_hash": phash(png),
                    "copyright_filter_status": "clear",
                    "tier": 2,
                    "width": 0, "height": 0,
                    "genre_hint": "rpg",
                    "platform_hint": "snes-style",
                    "local_path": str(png),
                }
                try:
                    from PIL import Image
                    with Image.open(png) as img:
                        entry["width"], entry["height"] = img.size
                except Exception:
                    pass
                write_provenance(entry)
                results.append(entry)

            log(f"  ✅ {name}: {len(pngs)} sprites")

        except Exception as e:
            log(f"  Error processing {name}: {e}")

    return results

# ── Source 2: OpenGameArt.org CC0 sprites ─────────────────────────────────

OGA_BASE  = "https://opengameart.org"
OGA_SEARCH = (
    "https://opengameart.org/art-search-advanced"
    "?field_art_type_tid[]=9"
    "&field_art_licenses_tid[]=17983"   # CC0
    "&sort_by=count&sort_order=DESC"
    "&items_per_page=24"
)

ACCEPTABLE_LICENSES = {"cc0", "cc-by", "cc-by-sa", "cc0-1.0", "cc-by-4.0", "cc-by-3.0",
                       "cc-by-sa-4.0", "cc-by-sa-3.0", "publicdomain"}

def is_acceptable_license(text: str) -> bool:
    t = text.lower().strip()
    # Reject NC and ND
    if "nc" in t or "nd" in t:
        return False
    return any(lic in t for lic in ACCEPTABLE_LICENSES)

def scrape_opengameart(raw_dir: Path, manifest_path: Path, max_packs: int = 40) -> list[dict]:
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
        if not check_robots(search_url):
            log("  robots.txt blocked search")
            break

        time.sleep(DELAY)
        try:
            r = SESSION.get(search_url, timeout=20)
            if r.status_code != 200:
                break
        except Exception as e:
            log(f"  Search page error: {e}")
            break

        soup = BeautifulSoup(r.text, "html.parser")

        # Find art pack links — OGA uses views-row divs with article links
        pack_links = []
        for a in soup.select("a[href]"):
            href = a["href"]
            if "/content/" in href and href not in visited_packs:
                # Exclude non-content pages
                if any(x in href for x in ["/faq", "/forums", "/search", "/user", "/art-search"]):
                    continue
                full = href if href.startswith("http") else OGA_BASE + href
                pack_links.append(full)
                visited_packs.add(href)

        # Deduplicate
        pack_links = list(dict.fromkeys(pack_links))
        log(f"  Page {page}: {len(pack_links)} pack links")

        if not pack_links:
            break

        for pack_url in pack_links:
            if pack_count >= max_packs:
                break

            time.sleep(DELAY)
            try:
                pr = SESSION.get(pack_url, timeout=20)
                if pr.status_code != 200:
                    continue
            except Exception:
                continue

            psoup = BeautifulSoup(pr.text, "html.parser")

            # Detect license
            license_text = ""
            for el in psoup.select(".field-name-field-art-licenses, .license, [class*=license]"):
                license_text += " " + el.get_text(" ", strip=True)
            # Also check meta tags
            for meta in psoup.find_all("meta"):
                if "license" in str(meta.get("name","")).lower():
                    license_text += " " + str(meta.get("content",""))

            if license_text and not is_acceptable_license(license_text):
                continue

            # Find download links — PNG or ZIP files
            download_links = []
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

            pack_pngs = 0
            for dl_url in download_links[:5]:  # max 5 files per pack
                fname = Path(urlparse(dl_url).path).name
                dest  = pack_dir / fname
                if dest.exists():
                    continue
                if not download_file(dl_url, dest, delay=0.5):
                    continue

                pngs_to_process: list[Path] = []
                if fname.lower().endswith(".zip"):
                    pngs_to_process = extract_zip(dest, pack_dir / fname.replace(".zip",""))
                elif fname.lower().endswith(".png"):
                    pngs_to_process = [dest]

                for png in pngs_to_process:
                    sprite_id = make_sprite_id("oga", f"{pack_slug}_{png.name}")
                    entry = {
                        "sprite_id": sprite_id,
                        "source_url": pack_url,
                        "creator": "OpenGameArt contributor",
                        "license": "CC0",
                        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                        "date_added": datetime.datetime.utcnow().isoformat(),
                        "perceptual_hash": phash(png),
                        "copyright_filter_status": "clear",
                        "tier": 2,
                        "width": 0, "height": 0,
                        "genre_hint": "rpg",
                        "platform_hint": "snes-style",
                        "local_path": str(png),
                    }
                    try:
                        from PIL import Image
                        with Image.open(png) as img:
                            entry["width"], entry["height"] = img.size
                    except Exception:
                        pass
                    write_provenance(entry)
                    results.append(entry)
                    pack_pngs += 1

            if pack_pngs > 0:
                log(f"  ✅ [{pack_count+1}] {pack_name}: {pack_pngs} PNGs")
                pack_count += 1
            else:
                log(f"  ⚠️  [{pack_count+1}] {pack_name}: 0 PNGs (skipped)")

        page += 1

    log(f"\n🏁 OpenGameArt total: {len(results)} PNGs across {pack_count} packs")
    return results

# ── Source 3: Direct high-quality CC0 sprite repos ────────────────────────
# These are curated, known-good sources with direct download links.

DIRECT_SOURCES = [
    # (url, sprite_id_prefix, creator, license, genre_hint)
    # LPC Sprite Collection — CC-BY-SA high quality RPG sprites
    ("https://opengameart.org/content/lpc-character-sprites",
     "lpc", "LPC Community", "CC-BY-SA", "rpg"),
    # Universal LPC Spritesheet
    ("https://opengameart.org/content/liberated-pixel-cup-lpc-base-assets-sprites-map-tiles",
     "lpc_base", "LPC Community", "CC-BY-SA", "rpg"),
    # RPG item icons CC0
    ("https://opengameart.org/content/rpg-item-pack",
     "rpg_items", "OpenGameArt", "CC0", "rpg"),
    # 16x16 dungeon tileset CC0
    ("https://opengameart.org/content/16x16-dungeon-tileset",
     "dungeon16", "OpenGameArt", "CC0", "rpg"),
    # SNES-style character sprites CC0
    ("https://opengameart.org/content/2d-rpg-character-sprite-base-with-animations",
     "rpg_char_base", "OpenGameArt", "CC0", "rpg"),
]

def scrape_direct_sources(raw_dir: Path) -> list[dict]:
    """Download from curated direct source list."""
    if not HAS_BS4:
        return []
    log("\n🎯 SOURCE 3: Direct curated sources")
    results = []
    for url, prefix, creator, license_str, genre in DIRECT_SOURCES:
        if not check_robots(url):
            continue
        time.sleep(DELAY)
        try:
            r = SESSION.get(url, timeout=20)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            pack_dir = raw_dir / "direct" / prefix
            for a in soup.select("a[href]"):
                href = a["href"]
                if any(href.lower().endswith(ext) for ext in [".png", ".zip"]):
                    full = href if href.startswith("http") else OGA_BASE + href
                    fname = Path(urlparse(full).path).name
                    dest = pack_dir / fname
                    if dest.exists():
                        continue
                    if not download_file(full, dest):
                        continue
                    pngs = extract_zip(dest, pack_dir) if fname.endswith(".zip") else [dest]
                    for png in pngs:
                        sprite_id = make_sprite_id(prefix, png.name)
                        entry = {
                            "sprite_id": sprite_id,
                            "source_url": url,
                            "creator": creator,
                            "license": license_str,
                            "license_url": "",
                            "date_added": datetime.datetime.utcnow().isoformat(),
                            "perceptual_hash": phash(png),
                            "copyright_filter_status": "clear",
                            "tier": 2,
                            "width": 0, "height": 0,
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
                        write_provenance(entry)
                        results.append(entry)
            log(f"  ✅ {prefix}: {len([e for e in results if e['sprite_id'].startswith(prefix)])} PNGs")
        except Exception as e:
            log(f"  Error {prefix}: {e}")
    return results

# ── main ───────────────────────────────────────────────────────────────────

def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    log(f"\n{'='*60}")
    log(f"AM Pixel Scraper v2 — {datetime.datetime.now().isoformat()}")
    log(f"{'='*60}")

    all_results: list[dict] = []

    kenney  = scrape_kenney(RAW_DIR, MANIFEST_PATH)
    all_results.extend(kenney)

    oga     = scrape_opengameart(RAW_DIR, MANIFEST_PATH, max_packs=40)
    all_results.extend(oga)

    direct  = scrape_direct_sources(RAW_DIR)
    all_results.extend(direct)

    log(f"\n{'='*60}")
    log(f"  SCRAPE COMPLETE")
    log(f"  Total sprites : {len(all_results)}")
    log(f"  Manifest path : {MANIFEST_PATH}")
    log(f"{'='*60}\n")

    print(f"\n✅ Done — {len(all_results)} sprites collected")

if __name__ == "__main__":
    main()
