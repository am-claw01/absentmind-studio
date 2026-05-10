# AM Pixel — Sprite Scraper Sources

All sources are verified permissively licensed (CC0, CC-BY, or CC-BY-SA).
This file documents every data source used by `scraper.py`.

---

## Source 1 — Kenney.nl (CC0)

| Field | Value |
|---|---|
| **Site** | https://kenney.nl |
| **License** | CC0 1.0 Universal (Public Domain) |
| **License URL** | https://creativecommons.org/publicdomain/zero/1.0/ |
| **Author** | Kenney (Kenney Vleugels) |
| **Method** | Direct ZIP download (no HTML scraping needed) |

### Packs

#### Tiny Town
- **Page:** https://kenney.nl/assets/tiny-town
- **ZIP:** `kenney_tiny-town.zip`
- **Expected sprites:** ~200 PNG tiles (16×16 isometric town tiles)
- **Content:** Buildings, roads, nature, vehicles in tiny isometric style

#### Micro Roguelike
- **Page:** https://kenney.nl/assets/micro-roguelike
- **ZIP:** `kenney_micro-roguelike.zip`
- **Expected sprites:** ~200+ PNG tiles (8×8 roguelike sprites)
- **Content:** Characters, monsters, items, dungeon tiles — directly relevant to AM Pixel

#### 1-Bit Pack
- **Page:** https://kenney.nl/assets/1-bit-pack
- **ZIP:** `kenney_1-bit-pack.zip`
- **Expected sprites:** 1000+ PNG sprites (16×16 monochrome)
- **Content:** Huge variety — UI, characters, tiles, icons, all in 1-bit pixel style

**Total expected from Kenney: ~1400+ PNG sprites**

---

## Source 2 — OpenGameArt.org CC0 Sprites

| Field | Value |
|---|---|
| **Site** | https://opengameart.org |
| **License filter** | CC0 1.0 (tid 17983) |
| **License URL** | https://creativecommons.org/publicdomain/zero/1.0/ |
| **Method** | HTML scraping of search results, then per-pack download |
| **Max packs** | 30 |
| **Search URL** | https://opengameart.org/art-search-advanced?field_art_type_tid[]=9&field_art_licenses_tid[]=17983&sort_by=count&sort_order=DESC |

### robots.txt compliance
The scraper fetches `https://opengameart.org/robots.txt` before scraping any HTML.
All requests are rate-limited to 1.5 seconds between calls.

### Content
OpenGameArt CC0 sprites sorted by download count — the top packs typically include:
- Character sprites and animations
- Tilesets (RPG, platformer, puzzle)
- UI elements and icons
- Item and object sprites
- Environment and effect sprites

**Total expected from OGA CC0: ~500–3000 PNG files depending on pack sizes**

---

## Source 3 — LPC Character Sprites (CC-BY-SA)

| Field | Value |
|---|---|
| **Page** | https://opengameart.org/content/lpc-character-sprites |
| **License** | CC-BY-SA 3.0 / 4.0 |
| **License URL** | https://creativecommons.org/licenses/by-sa/4.0/ |
| **Author** | Multiple LPC contributors (Liberated Pixel Cup) |
| **Method** | Direct page scrape + file download |

### About LPC
The Liberated Pixel Cup (LPC) was a game art competition hosted by the Free Software Foundation and OpenGameArt.org. All assets produced are CC-BY-SA, making them freely usable with attribution and share-alike.

The LPC character sprite set includes:
- Full character walk/run/attack/death animation sheets
- Multiple body types, hair styles, clothing layers
- 4-directional and 8-directional variants
- 64×64 sprite frames, suitable for training pixel art models

**Total expected from LPC: 50–200 PNG files (large spritesheets)**

---

## License Summary

| Source | SPDX Identifier | Training Use |
|---|---|---|
| Kenney.nl | CC0-1.0 | ✅ Unrestricted |
| OpenGameArt CC0 | CC0-1.0 | ✅ Unrestricted |
| LPC Sprites | CC-BY-SA-4.0 | ✅ With attribution + SA |

---

## Notes on Attribution (CC-BY / CC-BY-SA)

For any CC-BY or CC-BY-SA content used in training:
- Author and source URL are recorded in `TRAINING_PROVENANCE_MANIFEST.json`
- Attribution is preserved in the manifest and must be included in any model release notes
- Share-alike (SA) applies to derivative **works**, not trained model weights (legal grey area — consult counsel for commercial use)

---

## Adding New Sources

To add a new source to the scraper:

1. Verify the license is CC0, CC-BY, or CC-BY-SA
2. Check robots.txt compliance
3. Add a pack entry or new scrape function to `scraper.py`
4. Document the source in this file
5. The scraper will automatically record provenance in `TRAINING_PROVENANCE_MANIFEST.json`

---

*Last updated by scraper.py — see `scrape_log.md` for full download history.*
