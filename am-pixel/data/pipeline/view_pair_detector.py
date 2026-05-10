"""
data/pipeline/view_pair_detector.py
====================================
Identifies candidate sprite view pairs — same character, different facing
directions — within sprite sheet manifests for the AM Pixel pipeline.

The detector uses two cheap signals to propose pairs without any ML model:

1. **Palette overlap** (``compute_similarity``): sprites of the same character
   share most of their unique colours regardless of facing direction.  A
   palette-overlap ratio ≥ *similarity_threshold* (default 0.6) is required.

2. **Dimension match** (``compare_dimensions``): genuine view pairs always have
   identical pixel dimensions.

Public API
----------
compute_similarity(img1_path, img2_path) -> float
    Palette overlap ratio in [0, 1].
compare_dimensions(w1, h1, w2, h2) -> bool
    True when both sprites share the same pixel size.
find_candidate_pairs(sprite_manifest, similarity_threshold=0.6) -> list[dict]
    Full pairwise scan; returns dicts with keys:
    ``sprite_id_a``, ``sprite_id_b``, ``similarity``, ``source_sheet``.
main()
    CLI: loads a manifest, finds pairs, writes ``candidates.json``.

Requires: Python 3.14+, Pillow. No numpy / cv2.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

from PIL import Image


# ---------------------------------------------------------------------------
# Core comparison functions
# ---------------------------------------------------------------------------

def compute_similarity(img1_path: str | Path, img2_path: str | Path) -> float:
    """Compute the palette overlap ratio between two sprite images.

    The similarity is defined as the Jaccard index of the two sprites'
    unique-colour sets (ignoring fully-transparent pixels):

    .. code-block:: text

        similarity = |colours_A ∩ colours_B| / |colours_A ∪ colours_B|

    Parameters
    ----------
    img1_path, img2_path:
        Paths to the two sprite images.  Any format Pillow can open is
        accepted; images are converted to RGBA internally.

    Returns
    -------
    float
        Overlap ratio in ``[0.0, 1.0]``.  Returns ``0.0`` if both images
        contain no opaque pixels.

    Notes
    -----
    * Pixels with alpha < 128 are treated as transparent and excluded.
    * Colours are compared as ``(R, G, B)`` triples after stripping alpha.
    * Exact per-pixel colour matching is used (no bucketing / quantisation).
      For rough sprites sharing a small palette this works well; for
      photographic or highly-varied sources consider quantising first.

    Examples
    --------
    >>> sim = compute_similarity("hero_left.png", "hero_right.png")
    >>> 0.0 <= sim <= 1.0
    True
    """
    def _unique_colors(path: str | Path) -> frozenset[tuple[int, int, int]]:
        img = Image.open(path).convert("RGBA")
        colors: set[tuple[int, int, int]] = set()
        for r, g, b, a in img.getdata():
            if a >= 128:               # opaque enough to count
                colors.add((r, g, b))
        return frozenset(colors)

    colors_a = _unique_colors(img1_path)
    colors_b = _unique_colors(img2_path)

    union = colors_a | colors_b
    if not union:
        return 0.0
    intersection = colors_a & colors_b
    return len(intersection) / len(union)


def compare_dimensions(w1: int, h1: int, w2: int, h2: int) -> bool:
    """Return ``True`` when both sprites share the same pixel dimensions.

    Sprite view pairs (same character, different facing directions) always
    have identical width and height.  This is a necessary — though not
    sufficient — condition for pairing.

    Parameters
    ----------
    w1, h1:
        Width and height of the first sprite in pixels.
    w2, h2:
        Width and height of the second sprite in pixels.

    Returns
    -------
    bool
        ``True`` iff ``w1 == w2`` and ``h1 == h2``.

    Examples
    --------
    >>> compare_dimensions(16, 24, 16, 24)
    True
    >>> compare_dimensions(16, 24, 32, 32)
    False
    """
    return w1 == w2 and h1 == h2


# ---------------------------------------------------------------------------
# Pair finder
# ---------------------------------------------------------------------------

def find_candidate_pairs(
    sprite_manifest: list[dict],
    similarity_threshold: float = 0.6,
) -> list[dict]:
    """Identify candidate sprite view pairs from a provenance manifest.

    Performs an O(n²) pairwise scan over all sprites in *sprite_manifest*.
    For every distinct pair ``(A, B)`` the function:

    1. Checks that ``A`` and ``B`` share the same pixel dimensions via
       :func:`compare_dimensions`.
    2. Computes the palette overlap ratio via :func:`compute_similarity`.
    3. Emits a candidate record if the ratio meets *similarity_threshold*.

    Parameters
    ----------
    sprite_manifest:
        List of provenance dicts.  Each entry must contain at minimum:

        * ``"sprite_id"``    (str)  — unique identifier
        * ``"width"``        (int)  — sprite width in pixels
        * ``"height"``       (int)  — sprite height in pixels

        Optionally:

        * ``"image_path"``   (str)  — absolute/relative path to the PNG
        * ``"source_sheet"`` (str)  — identifier of the parent sprite sheet

        If ``"image_path"`` is absent the entry is skipped with a warning.

    similarity_threshold:
        Minimum Jaccard palette overlap (inclusive) to emit a pair.
        Default is ``0.6``.

    Returns
    -------
    list[dict]
        Sorted (by descending similarity) list of candidate records, each
        containing:

        ``sprite_id_a`` (str), ``sprite_id_b`` (str),
        ``similarity`` (float, 4 d.p.), ``source_sheet`` (str).

        ``source_sheet`` is set to the value from sprite A if both share
        the same sheet, otherwise ``"multiple"``.

    Notes
    -----
    Pairs are unordered: ``(A, B)`` and ``(B, A)`` are not both emitted.

    For large manifests (>1000 sprites) consider pre-filtering by
    ``source_sheet`` or dimensions before calling this function.

    Examples
    --------
    ::

        manifest = read_manifest("data/pipeline/manifest.json")
        pairs = find_candidate_pairs(manifest, similarity_threshold=0.65)
        for p in pairs[:5]:
            print(p["sprite_id_a"], "↔", p["sprite_id_b"], p["similarity"])
    """
    # Pre-filter: skip entries missing image_path
    valid: list[dict] = []
    for entry in sprite_manifest:
        if "image_path" not in entry:
            print(
                f"[view_pair_detector] WARNING: sprite '{entry.get('sprite_id', '?')}' "
                "has no 'image_path'; skipping.",
                file=sys.stderr,
            )
            continue
        valid.append(entry)

    candidates: list[dict] = []

    for a, b in itertools.combinations(valid, 2):
        # Dimension check (fast, no I/O)
        if not compare_dimensions(a["width"], a["height"], b["width"], b["height"]):
            continue

        # Palette overlap (opens both images)
        try:
            sim = compute_similarity(a["image_path"], b["image_path"])
        except (FileNotFoundError, OSError) as exc:
            print(
                f"[view_pair_detector] WARNING: could not open image for pair "
                f"({a['sprite_id']!r}, {b['sprite_id']!r}): {exc}",
                file=sys.stderr,
            )
            continue

        if sim < similarity_threshold:
            continue

        # Determine source_sheet
        sheet_a = a.get("source_sheet", "")
        sheet_b = b.get("source_sheet", "")
        if sheet_a and sheet_a == sheet_b:
            source_sheet = sheet_a
        elif sheet_a and not sheet_b:
            source_sheet = sheet_a
        elif sheet_b and not sheet_a:
            source_sheet = sheet_b
        else:
            source_sheet = "multiple"

        candidates.append({
            "sprite_id_a": a["sprite_id"],
            "sprite_id_b": b["sprite_id"],
            "similarity":  round(sim, 4),
            "source_sheet": source_sheet,
        })

    # Sort by descending similarity
    candidates.sort(key=lambda x: x["similarity"], reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """Command-line entry point for the view-pair detector.

    Loads a sprite manifest JSON, finds candidate view pairs, and writes
    the results to a ``candidates.json`` file.

    Arguments
    ---------
    --manifest
        Path to a provenance manifest JSON (list of sprite dicts).
    --output
        Destination for the ``candidates.json`` output.
        Defaults to ``candidates.json`` in the current directory.
    --threshold
        Minimum palette-overlap similarity to emit a pair.  Default 0.6.

    Examples
    --------
    ::

        python view_pair_detector.py --manifest data/pipeline/manifest.json
        python view_pair_detector.py \\
            --manifest data/pipeline/manifest.json \\
            --output data/pipeline/candidates.json \\
            --threshold 0.70
    """
    parser = argparse.ArgumentParser(
        prog="view_pair_detector",
        description="AM Pixel — sprite view-pair candidate detector",
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to sprite manifest JSON (list of provenance dicts)",
    )
    parser.add_argument(
        "--output",
        default="candidates.json",
        help="Output path for candidates.json (default: candidates.json)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Minimum palette-overlap similarity (default: 0.6)",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"[view_pair_detector] ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    sprite_manifest: list[dict] = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(sprite_manifest, list):
        print("[view_pair_detector] ERROR: manifest must be a JSON array.", file=sys.stderr)
        sys.exit(1)

    print(
        f"[view_pair_detector] Scanning {len(sprite_manifest)} sprites "
        f"(threshold={args.threshold}) …"
    )

    pairs = find_candidate_pairs(sprite_manifest, similarity_threshold=args.threshold)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(pairs, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[view_pair_detector] Found {len(pairs)} candidate pair(s) → {output_path}")
    if pairs:
        print("\nTop results:")
        for p in pairs[:10]:
            print(
                f"  {p['sprite_id_a']:30s} ↔ {p['sprite_id_b']:30s}"
                f"  sim={p['similarity']:.4f}  sheet={p['source_sheet']}"
            )


if __name__ == "__main__":
    main()
