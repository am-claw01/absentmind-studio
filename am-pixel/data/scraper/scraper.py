#!/usr/bin/env python3.14
"""
AM Pixel Sprite Scraper
=======================
Downloads permissively-licensed sprite packs from Kenney.nl and OpenGameArt.org.
Writes provenance entries to TRAINING_PROVENANCE_MANIFEST.json BEFORE saving sprites.
Logs all activity to data/scraper/scrape_log.md.
Respects robots.txt and rate-limits requests (1.5s delay).
Accepted licenses: CC0, CC-BY, CC-BY-SA.
"""

import os
import sys
import json
import time
import zipfile
import hashlib
import datetime
import re
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse, urljoin

# ── graceful import of requests ────────────────────────────────────────────────
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("ERROR: 'requests' not installed. Run: python3.14 -m pip install requests --break-system-packages")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    print("WARNING: 'beautifulsoup4' not installed — OpenGameArt HTML scraping will be limited.")
    print("         Run: python3.14 -m pip install beautifulsoup4 --break-system-packages")

# ── paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent.resolve()
DATA_DIR     = SCRIPT_DIR.parent.resolve()           # data/
PROJECT_ROOT = DATA_DIR.parent.resolve()             # am-pixel/

RAW_DIR      = DATA_DIR / "raw" / "sprites"
MANIFEST_PATH = DATA_DIR / "TRAINING_PROVENANCE_MANIFEST.json"
LOG_PATH     = SCRIPT_DIR / "scrape_log.md"

# Cache for robots.txt decisions
_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}

# User-agent
UA = "AMPixelScraper/1.0 (+https://github.com/absentmind-studio/am-pixel; respectful bot)"

HEADERS = {"User-Agent": UA}

# ──────────────────────────────────────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────────────────────────────────────

def write_scrape_log(entry: str) -> None:
    """Append a timestamped entry to the scrape log markdown file."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n---\n**{timestamp}**\n{entry}\n")
    print(f"[LOG] {entry[:120]}")


# ──────────────────────────────────────────────────────────────────────────────
# ROBOTS.TXT
# ──────────────────────────────────────────────────────────────────────────────

def check_robots(domain: str, path: str, session: requests.Session) -> bool:
    """
    Return True if we are allowed to fetch `path` on `domain`.
    Caches the parsed robots.txt per domain.
    domain should be like 'https://opengameart.org'
    """
    if domain not in _robots_cache:
        robots_url = domain.rstrip("/") + "/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        try:
            resp = session.get(robots_url, headers=HEADERS, timeout=10)
            rp.parse(resp.text.splitlines())
            write_scrape_log(f"✅ Fetched robots.txt from {robots_url} (HTTP {resp.status_code})")
        except Exception as e:
            write_scrape_log(f"⚠️ Could not fetch robots.txt for {domain}: {e} — assuming allowed")
            rp.allow_all = True
        _robots_cache[domain] = rp

    rp = _robots_cache[domain]
    allowed = rp.can_fetch(UA, path)
    if not allowed:
        write_scrape_log(f"🚫 robots.txt DISALLOWS {domain}{path}")
    return allowed


# ──────────────────────────────────────────────────────────────────────────────
# MANIFEST
# ──────────────────────────────────────────────────────────────────────────────

def load_manifest(manifest_path: Path) -> list:
    """Load existing manifest or return empty list."""
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return data if isinstance(data, list) else []
            except json.JSONDecodeError:
                return []
    return []


def save_manifest(manifest_path: Path, entries: list) -> None:
    """Atomically write manifest to disk."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    tmp.replace(manifest_path)


def write_provenance(
    manifest_path: Path,
    source_url: str,
    license_spdx: str,
    license_url: str,
    pack_name: str,
    author: str,
    local_paths: list[str],
    extra: dict | None = None,
) -> dict:
    """
    Write a provenance entry to the manifest BEFORE the file is finalised.
    Returns the entry dict.
    """
    entries = load_manifest(manifest_path)
    entry = {
        "id": hashlib.sha1(source_url.encode()).hexdigest()[:12],
        "pack_name": pack_name,
        "source_url": source_url,
        "author": author,
        "license": license_spdx,
        "license_url": license_url,
        "local_paths": local_paths,
        "scraped_at": datetime.datetime.utcnow().isoformat() + "Z",
        "extra": extra or {},
    }
    entries.append(entry)
    save_manifest(manifest_path, entries)
    return entry


# ──────────────────────────────────────────────────────────────────────────────
# FILE DOWNLOAD
# ──────────────────────────────────────────────────────────────────────────────

def make_session() -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry = Retry(total=4, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session


def download_file(url: str, dest: Path, session: requests.Session, delay: float = 1.5) -> bool:
    """
    Download a file to `dest`. Creates parent directories.
    Returns True on success, False on failure.
    Sleeps `delay` seconds BEFORE the request (rate limiting).
    """
    time.sleep(delay)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        write_scrape_log(f"⏭️  Already exists, skipping: {dest.name}")
        return True

    try:
        write_scrape_log(f"⬇️  Downloading: {url}")
        with session.get(url, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            with open(dest, "wb") as f:
                downloaded = 0
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            write_scrape_log(f"✅ Saved {dest.name} ({downloaded:,} bytes)")
            return True
    except requests.HTTPError as e:
        write_scrape_log(f"❌ HTTP error downloading {url}: {e}")
        if dest.exists():
            dest.unlink()
        return False
    except Exception as e:
        write_scrape_log(f"❌ Error downloading {url}: {e}")
        if dest.exists():
            dest.unlink()
        return False


# ──────────────────────────────────────────────────────────────────────────────
# ZIP EXTRACTION
# ──────────────────────────────────────────────────────────────────────────────

def extract_zip(zip_path: Path, extract_to: Path) -> list[str]:
    """
    Extract a ZIP file. Returns list of absolute paths to extracted PNG files.
    """
    png_paths = []
    extract_to.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            members = zf.namelist()
            write_scrape_log(f"📦 Extracting {zip_path.name} ({len(members)} entries) → {extract_to}")
            for member in members:
                # Security: skip path traversal attempts
                safe = Path(member)
                if ".." in safe.parts:
                    write_scrape_log(f"⚠️  Skipping unsafe path in ZIP: {member}")
                    continue
                zf.extract(member, extract_to)
                if member.lower().endswith(".png"):
                    png_paths.append(str(extract_to / member))
        write_scrape_log(f"✅ Extracted {len(png_paths)} PNG(s) from {zip_path.name}")
    except zipfile.BadZipFile as e:
        write_scrape_log(f"❌ Bad ZIP file {zip_path}: {e}")
    except Exception as e:
        write_scrape_log(f"❌ Error extracting {zip_path}: {e}")
    return png_paths


# ──────────────────────────────────────────────────────────────────────────────
# SOURCE 1 — KENNEY.NL (CC0)
# ──────────────────────────────────────────────────────────────────────────────

KENNEY_PACKS = [
    {
        "name": "Kenney Tiny Town",
        "page_url": "https://kenney.nl/assets/tiny-town",
        "zip_url": "https://kenney.nl/media/pages/assets/tiny-town/1a5e0f0e72-1707312668/kenney_tiny-town.zip",
        "zip_name": "kenney_tiny-town.zip",
    },
    {
        "name": "Kenney Micro Roguelike",
        "page_url": "https://kenney.nl/assets/micro-roguelike",
        "zip_url": "https://kenney.nl/media/pages/assets/micro-roguelike/a3f69db8a7-1707312668/kenney_micro-roguelike.zip",
        "zip_name": "kenney_micro-roguelike.zip",
    },
    {
        "name": "Kenney 1-Bit Pack",
        "page_url": "https://kenney.nl/assets/1-bit-pack",
        "zip_url": "https://kenney.nl/media/pages/assets/1-bit-pack/c813f5e2b9-1710347567/kenney_1-bit-pack.zip",
        "zip_name": "kenney_1-bit-pack.zip",
    },
]


def scrape_kenney(raw_dir: Path, manifest_path: Path) -> list[dict]:
    """
    Download Kenney.nl CC0 sprite packs.
    Returns list of provenance entry dicts.
    """
    write_scrape_log("=" * 60)
    write_scrape_log("🎮 SOURCE 1: Kenney.nl CC0 sprite packs")
    write_scrape_log("=" * 60)

    session = make_session()
    entries = []
    kenney_dir = raw_dir / "kenney"

    for pack in KENNEY_PACKS:
        pack_slug = pack["zip_name"].replace(".zip", "")
        pack_dir  = kenney_dir / pack_slug
        zip_dest  = kenney_dir / pack["zip_name"]

        write_scrape_log(f"\n📁 Pack: {pack['name']}")

        # Write provenance BEFORE downloading (placeholder paths)
        prov_entry = write_provenance(
            manifest_path=manifest_path,
            source_url=pack["page_url"],
            license_spdx="CC0-1.0",
            license_url="https://creativecommons.org/publicdomain/zero/1.0/",
            pack_name=pack["name"],
            author="Kenney (Kenney.nl)",
            local_paths=[str(zip_dest)],
            extra={"zip_url": pack["zip_url"], "status": "pending"},
        )

        # Download the ZIP
        ok = download_file(pack["zip_url"], zip_dest, session, delay=1.5)
        if not ok:
            write_scrape_log(f"❌ Failed to download {pack['name']}, skipping.")
            continue

        # Extract PNGs
        png_paths = extract_zip(zip_dest, pack_dir)

        # Update provenance with real paths
        manifest_entries = load_manifest(manifest_path)
        for me in manifest_entries:
            if me["id"] == prov_entry["id"]:
                me["local_paths"] = png_paths if png_paths else [str(zip_dest)]
                me["extra"]["status"] = "complete"
                me["extra"]["png_count"] = len(png_paths)
                break
        save_manifest(manifest_path, manifest_entries)

        prov_entry["local_paths"] = png_paths
        entries.append(prov_entry)
        write_scrape_log(f"✅ {pack['name']}: {len(png_paths)} PNGs extracted")

    write_scrape_log(f"\n🏁 Kenney total: {sum(len(e.get('local_paths', [])) for e in entries)} PNGs across {len(entries)} packs")
    return entries


# ──────────────────────────────────────────────────────────────────────────────
# SOURCE 2 & 3 — OPENGAMEART.ORG
# ──────────────────────────────────────────────────────────────────────────────

OGA_BASE = "https://opengameart.org"
OGA_DOMAIN = OGA_BASE

# CC0 search (tid 17983 = CC0)
OGA_CC0_SEARCH = (
    "https://opengameart.org/art-search-advanced"
    "?field_art_type_tid[]=9"
    "&field_art_licenses_tid[]=17983"
    "&sort_by=count&sort_order=DESC"
)

# LPC character sprites (CC-BY-SA)
LPC_URL = "https://opengameart.org/content/lpc-character-sprites"

LICENSE_MAP = {
    "CC0":        ("CC0-1.0",    "https://creativecommons.org/publicdomain/zero/1.0/"),
    "CC-BY":      ("CC-BY-4.0",  "https://creativecommons.org/licenses/by/4.0/"),
    "CC-BY-SA":   ("CC-BY-SA-4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
    "GPL":        None,   # excluded
    "OGA-BY":     None,   # excluded
}


def _detect_license_from_text(text: str) -> tuple[str, str] | None:
    """Try to identify a CC license from page text. Returns (spdx, url) or None."""
    txt = text.upper()
    if "CC0" in txt or "PUBLIC DOMAIN" in txt:
        return LICENSE_MAP["CC0"]
    if "CC-BY-SA" in txt or "CC BY-SA" in txt or "ATTRIBUTION-SHAREALIKE" in txt:
        return LICENSE_MAP["CC-BY-SA"]
    if "CC-BY" in txt or "CC BY" in txt or "ATTRIBUTION" in txt:
        return LICENSE_MAP["CC-BY"]
    return None


def _parse_oga_pack_page(url: str, session: requests.Session, raw_dir: Path, manifest_path: Path) -> dict | None:
    """
    Visit a single OpenGameArt art page, find download links, download PNGs/ZIPs.
    Returns a provenance entry dict or None on failure.
    """
    if not HAS_BS4:
        write_scrape_log("⚠️  BeautifulSoup4 not available — skipping HTML parse")
        return None

    parsed = urlparse(url)
    if not check_robots(OGA_DOMAIN, parsed.path, session):
        return None

    time.sleep(1.5)
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        write_scrape_log(f"❌ Could not fetch pack page {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Pack title
    title_tag = soup.find("h1")
    pack_name = title_tag.get_text(strip=True) if title_tag else url.split("/")[-1]

    # Author
    author = "Unknown"
    author_tag = soup.find("a", href=re.compile(r"/users/"))
    if author_tag:
        author = author_tag.get_text(strip=True)

    # License detection — look for license widget text
    license_section = soup.find("div", class_=re.compile(r"license|field-name-field-art-licenses", re.I))
    license_text = license_section.get_text() if license_section else resp.text[:3000]
    license_info = _detect_license_from_text(license_text)

    if license_info is None:
        write_scrape_log(f"⚠️  Could not identify acceptable license for '{pack_name}' at {url} — skipping")
        return None

    spdx, license_url = license_info

    # Find download links (PNG / ZIP)
    download_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(OGA_BASE, href)
        lower = href.lower()
        if any(lower.endswith(ext) for ext in [".png", ".zip", ".tar.gz", ".7z"]):
            download_links.append(full)
        # OGA file download page pattern
        if "/files/" in lower and "download" not in lower:
            download_links.append(full)

    # Also check for /sites/default/files/ patterns
    for tag in soup.find_all(["a", "link"], href=re.compile(r"/sites/default/files/", re.I)):
        href = tag.get("href", "")
        download_links.append(urljoin(OGA_BASE, href))

    download_links = list(dict.fromkeys(download_links))  # deduplicate, preserve order

    if not download_links:
        write_scrape_log(f"⚠️  No download links found for '{pack_name}' at {url}")
        return None

    slug = re.sub(r"[^\w-]", "_", pack_name.lower())[:50]
    pack_dir = raw_dir / "opengameart" / slug

    # Write provenance BEFORE downloading
    prov_entry = write_provenance(
        manifest_path=manifest_path,
        source_url=url,
        license_spdx=spdx,
        license_url=license_url,
        pack_name=pack_name,
        author=author,
        local_paths=[],
        extra={"status": "pending", "download_links": download_links[:5]},
    )

    all_pngs = []
    for dl_url in download_links[:6]:  # cap per pack
        dl_parsed = urlparse(dl_url)
        filename = Path(dl_parsed.path).name or "download"
        dest = pack_dir / filename

        ok = download_file(dl_url, dest, session, delay=1.5)
        if not ok:
            continue

        if dest.suffix.lower() == ".zip":
            pngs = extract_zip(dest, pack_dir)
            all_pngs.extend(pngs)
        elif dest.suffix.lower() == ".png":
            all_pngs.append(str(dest))

    if not all_pngs:
        write_scrape_log(f"⚠️  No PNGs obtained for '{pack_name}'")

    # Update provenance
    manifest_entries = load_manifest(manifest_path)
    for me in manifest_entries:
        if me["id"] == prov_entry["id"]:
            me["local_paths"] = all_pngs
            me["extra"]["status"] = "complete"
            me["extra"]["png_count"] = len(all_pngs)
            break
    save_manifest(manifest_path, manifest_entries)

    prov_entry["local_paths"] = all_pngs
    write_scrape_log(f"✅ '{pack_name}' [{spdx}]: {len(all_pngs)} PNG(s)")
    return prov_entry


def scrape_opengameart(raw_dir: Path, manifest_path: Path, max_packs: int = 30) -> list[dict]:
    """
    Scrape OpenGameArt.org for CC0 sprite packs + LPC sprites (CC-BY-SA).
    Returns list of provenance entry dicts.
    """
    write_scrape_log("=" * 60)
    write_scrape_log("🎨 SOURCE 2 & 3: OpenGameArt.org (CC0 + LPC CC-BY-SA)")
    write_scrape_log("=" * 60)

    if not HAS_BS4:
        write_scrape_log("❌ BeautifulSoup4 not available — cannot parse HTML. Skipping OpenGameArt scrape.")
        return []

    session = make_session()
    entries = []

    # ── SOURCE 3: LPC Character Sprites (CC-BY-SA) — always fetch this one ──
    write_scrape_log("\n🗡️  SOURCE 3: LPC Character Sprites (CC-BY-SA)")
    lpc_parsed = urlparse(LPC_URL)
    if check_robots(OGA_DOMAIN, lpc_parsed.path, session):
        lpc_entry = _parse_oga_pack_page(LPC_URL, session, raw_dir, manifest_path)
        if lpc_entry:
            entries.append(lpc_entry)
    else:
        write_scrape_log(f"🚫 robots.txt blocks LPC URL")

    # ── SOURCE 2: CC0 search results ─────────────────────────────────────────
    write_scrape_log(f"\n🔍 SOURCE 2: OpenGameArt CC0 search — up to {max_packs} packs")
    search_parsed = urlparse(OGA_CC0_SEARCH)
    if not check_robots(OGA_DOMAIN, search_parsed.path, session):
        write_scrape_log("🚫 robots.txt blocks CC0 search page")
        return entries

    page_num = 0
    pack_count = 0
    visited_pack_urls: set[str] = set()

    # Add LPC URL to visited so we don't double-fetch
    visited_pack_urls.add(LPC_URL)

    while pack_count < max_packs:
        page_url = OGA_CC0_SEARCH + (f"&page={page_num}" if page_num > 0 else "")
        write_scrape_log(f"\n📄 Fetching search results page {page_num}: {page_url}")

        time.sleep(1.5)
        try:
            resp = session.get(page_url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            write_scrape_log(f"❌ Failed to fetch search page: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # Find art pack links — OGA uses views-row divs with links to /content/...
        pack_links = []
        for a in soup.find_all("a", href=re.compile(r"^/content/")):
            href = a["href"]
            full = urljoin(OGA_BASE, href)
            # Skip tag/category pages and other non-art pages
            if full not in visited_pack_urls and "?" not in href:
                pack_links.append(full)
                visited_pack_urls.add(full)

        # Deduplicate while preserving order
        pack_links = list(dict.fromkeys(pack_links))

        if not pack_links:
            write_scrape_log("ℹ️  No more pack links found — end of results.")
            break

        write_scrape_log(f"   Found {len(pack_links)} pack link(s) on this page")

        for pack_url in pack_links:
            if pack_count >= max_packs:
                break
            write_scrape_log(f"\n   [{pack_count + 1}/{max_packs}] Processing: {pack_url}")
            entry = _parse_oga_pack_page(pack_url, session, raw_dir, manifest_path)
            if entry:
                entries.append(entry)
                pack_count += 1

        page_num += 1
        if pack_count >= max_packs:
            break

    write_scrape_log(f"\n🏁 OpenGameArt total: {sum(len(e.get('local_paths', [])) for e in entries)} PNGs across {len(entries)} packs")
    return entries


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  AM Pixel Sprite Scraper")
    print(f"  Started: {datetime.datetime.utcnow().isoformat()}Z")
    print(f"  RAW_DIR: {RAW_DIR}")
    print(f"  MANIFEST: {MANIFEST_PATH}")
    print(f"  LOG: {LOG_PATH}")
    print("=" * 70)

    # Ensure directories exist
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)

    # Init log
    if not LOG_PATH.exists():
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write("# AM Pixel Sprite Scrape Log\n\n")
            f.write(f"Scraper started: {datetime.datetime.utcnow().isoformat()}Z\n")

    write_scrape_log(f"🚀 Scraper started — PID {os.getpid()}")

    all_entries: list[dict] = []

    # ── Source 1: Kenney ──────────────────────────────────────────────────────
    print("\n[1/3] Scraping Kenney.nl...")
    kenney_entries = scrape_kenney(RAW_DIR, MANIFEST_PATH)
    all_entries.extend(kenney_entries)

    # ── Source 2 & 3: OpenGameArt ────────────────────────────────────────────
    if HAS_BS4:
        print("\n[2/3] Scraping OpenGameArt.org (CC0)...")
        print("[3/3] LPC sprites included in OGA scrape...")
        oga_entries = scrape_opengameart(RAW_DIR, MANIFEST_PATH, max_packs=30)
        all_entries.extend(oga_entries)
    else:
        print("\n[2/3] SKIPPED — beautifulsoup4 not installed")
        print("[3/3] SKIPPED — beautifulsoup4 not installed")

    # ── Summary ───────────────────────────────────────────────────────────────
    total_pngs  = sum(len(e.get("local_paths", [])) for e in all_entries)
    total_packs = len(all_entries)

    summary = (
        f"\n{'=' * 60}\n"
        f"  SCRAPE COMPLETE\n"
        f"  Packs processed : {total_packs}\n"
        f"  Total PNG files : {total_pngs}\n"
        f"  Manifest entries: {len(load_manifest(MANIFEST_PATH))}\n"
        f"{'=' * 60}"
    )
    print(summary)
    write_scrape_log(summary)

    # Per-pack breakdown
    print("\nPer-pack breakdown:")
    for e in all_entries:
        n = len(e.get("local_paths", []))
        print(f"  [{e['license']:15s}] {e['pack_name'][:50]:50s} — {n} PNG(s)")

    write_scrape_log(f"✅ Scraper finished — {total_packs} packs, {total_pngs} PNGs")

    return all_entries


if __name__ == "__main__":
    main()
