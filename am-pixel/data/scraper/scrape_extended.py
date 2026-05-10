#!/usr/bin/env python3
"""
AM Pixel — Extended Kenney acquisition script.
Downloads additional Kenney packs and processes OGA direct sources.
"""
import datetime, json, time, zipfile, re, sys
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("pip install requests beautifulsoup4")

BASE      = Path(__file__).parent.parent.parent  # am-pixel/
RAW_DIR   = BASE / "data" / "raw" / "sprites"
MANIFEST  = BASE / "data" / "TRAINING_PROVENANCE_MANIFEST.json"
LOG       = BASE / "data" / "scraper" / "scrape_log.md"
DELAY     = 1.2

sess = requests.Session()
sess.headers["User-Agent"] = "AMPixelScraper/2 (educational pixel art dataset)"

def log(m):
    print(m)
    with open(LOG, "a") as f:
        f.write(f"{datetime.datetime.now().isoformat()} {m}\n")

def phash(path):
    try:
        from PIL import Image
        img = Image.open(path).convert("L").resize((8,8))
        px  = list(img.getdata())
        mn  = sum(px)/len(px)
        return format(int("".join("1" if p>=mn else "0" for p in px),2),"016x")
    except Exception:
        import hashlib
        return hashlib.md5(path.read_bytes()).hexdigest()[:16]

def append_provenance(entry):
    try:
        data = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
    except Exception:
        data = []
    data.append(entry)
    MANIFEST.write_text(json.dumps(data, indent=2))

def get(url, **kw):
    time.sleep(DELAY)
    return sess.get(url, timeout=25, **kw)

def dl(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return True
    try:
        r = get(url, stream=True)
        if r.status_code != 200:
            return False
        with open(dest, "wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
        return True
    except Exception as e:
        log(f"  DL error {url}: {e}")
        return False

def extract(zp, to):
    to.mkdir(parents=True, exist_ok=True)
    pngs = []
    try:
        with zipfile.ZipFile(zp) as z:
            for n in z.namelist():
                if n.lower().endswith(".png") and not n.startswith("__"):
                    z.extract(n, to)
                    pngs.append(to / n)
    except Exception as e:
        log(f"  ZIP error: {e}")
    return pngs

def record(png, source_url, creator, license_str, prefix):
    try:
        from PIL import Image
        w, h = Image.open(png).size
    except Exception:
        w, h = 0, 0
    slug = re.sub(r"[^a-z0-9]","_", png.name.lower().replace(".png",""))[:60]
    entry = dict(
        sprite_id    = f"{prefix}_{slug}"[:80],
        source_url   = source_url,
        creator      = creator,
        license      = license_str,
        license_url  = "",
        date_added   = datetime.datetime.now(datetime.UTC).isoformat(),
        perceptual_hash = phash(png),
        copyright_filter_status = "clear",
        tier=2, width=w, height=h,
        genre_hint="rpg", platform_hint="snes-style",
        local_path=str(png),
    )
    append_provenance(entry)
    return entry

# ── Kenney packs ──────────────────────────────────────────────────────────
KENNEY_SLUGS = [
    "animal-pack-redux", "rpg-base", "sci-fi-platformer",
    "creature-pack", "roguelike-rpg-pack", "top-down-tanks-redux",
    "monochrome-rpg", "input-prompts-pixel-16",
    "medieval-rts", "isometric-game-assets-pixel",
    "pixel-platformer-blocks", "pixel-platformer-characters",
    "ui-pack-rpg-expansion",
]

total = 0
for slug in KENNEY_SLUGS:
    url = f"https://kenney.nl/assets/{slug}"
    log(f"\n[Kenney] {slug}")
    try:
        r = get(url)
        if r.status_code != 200:
            log(f"  HTTP {r.status_code}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        zip_url = None
        for a in soup.find_all("a", href=True):
            if ".zip" in a["href"]:
                h = a["href"]
                zip_url = h if h.startswith("http") else f"https://kenney.nl{h}"
                break
        if not zip_url:
            log("  No ZIP found")
            continue
        zdest = RAW_DIR / "kenney" / f"{slug}.zip"
        if not dl(zip_url, zdest):
            continue
        pngs = extract(zdest, RAW_DIR / "kenney" / slug)
        for png in pngs:
            record(png, zip_url, "Kenney.nl", "CC0", "kenney")
        log(f"  ✅ {len(pngs)} sprites")
        total += len(pngs)
    except Exception as e:
        log(f"  Error: {e}")

# ── OpenGameArt direct packs ──────────────────────────────────────────────
OGA_PACKS = [
    ("https://opengameart.org/content/dawnlike-16x16-universal-rogue-like-tileset-v181", "dawnlike", "CC0"),
    ("https://opengameart.org/content/tiny-16-basic", "tiny16", "CC0"),
    ("https://opengameart.org/content/rpg-tiles-cobble-stone-paths-town-objects", "rpg_tiles", "CC0"),
    ("https://opengameart.org/content/16x16-fantasy-tileset", "fantasy16", "CC0"),
    ("https://opengameart.org/content/simple-broad-purpose-tileset", "broad_tileset", "CC0"),
    ("https://opengameart.org/content/2d-rpg-character-sprite-base-with-animations", "rpg_char", "CC0"),
    ("https://opengameart.org/content/zelda-like-tilesets-and-sprites", "zelda_like", "CC-BY"),
    ("https://opengameart.org/content/16x16-dungeon-tileset", "dungeon16", "CC0"),
    ("https://opengameart.org/content/16x16-fantasy-rpg-enemies", "fantasy_enemies", "CC0"),
    ("https://opengameart.org/content/rpg-enemies-11-dragons", "dragons", "CC-BY"),
    ("https://opengameart.org/content/eight-8-bit-style-characters", "8bit_chars", "CC0"),
    ("https://opengameart.org/content/pixel-art-ui-pack", "pixel_ui", "CC0"),
    ("https://opengameart.org/content/animated-pixel-adventurer", "adventurer", "CC0"),
    ("https://opengameart.org/content/character-sprite-pack", "char_pack", "CC0"),
    ("https://opengameart.org/content/forest-tileset", "forest_tiles", "CC0"),
    ("https://opengameart.org/content/lpc-medieval-village-decorations", "lpc_village", "CC-BY-SA"),
]

OGA_BASE = "https://opengameart.org"
for pack_url, prefix, lic in OGA_PACKS:
    log(f"\n[OGA] {prefix}")
    try:
        r = get(pack_url)
        if r.status_code != 200:
            log(f"  HTTP {r.status_code}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        pack_dir = RAW_DIR / "opengameart" / prefix
        found = 0
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if any(href.lower().endswith(ext) for ext in [".png", ".zip"]):
                full = href if href.startswith("http") else OGA_BASE + href
                fname = Path(urlparse(full).path).name
                dest = pack_dir / fname
                if not dl(full, dest):
                    continue
                pngs = extract(dest, pack_dir) if fname.endswith(".zip") else [dest]
                for png in pngs:
                    record(png, pack_url, "OpenGameArt", lic, prefix)
                    found += 1
        log(f"  ✅ {found} sprites")
        total += found
    except Exception as e:
        log(f"  Error: {e}")

log(f"\n{'='*50}")
log(f"Extended scrape complete — {total} new sprites")
print(f"\n✅ Extended scrape done — {total} new sprites acquired")
