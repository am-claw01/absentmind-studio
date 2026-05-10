"""
data/pipeline/splitter.py
=========================
Dataset split utilities for AM Pixel training pipelines.

Provides:
  - split_dataset()       — deterministic random shuffle + train/val split
  - split_by_genre()      — stratified split keyed on ``genre_hint`` field
  - write_split_manifest()— write train.json / val.json to a directory
  - load_split()          — load a split JSON file back into a list of IDs
  - main()                — argparse CLI

Requires: Python 3.14+, standard library only.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Core split functions
# ---------------------------------------------------------------------------

def split_dataset(
    sprite_ids: list[str],
    validation_ratio: float = 0.10,
    seed: int = 42,
) -> tuple[list[str], list[str]]:
    """Deterministically shuffle *sprite_ids* and split into train / val sets.

    Parameters
    ----------
    sprite_ids:
        Flat list of sprite ID strings to split.
    validation_ratio:
        Fraction of sprites to reserve for validation. Must be in ``(0, 1)``.
        Default is ``0.10`` (10 %).
    seed:
        Integer seed for :class:`random.Random` to ensure reproducibility
        across runs and Python versions.

    Returns
    -------
    tuple[list[str], list[str]]
        ``(train_ids, val_ids)`` — each is a new list; the input is not
        mutated.

    Raises
    ------
    ValueError
        If *validation_ratio* is not strictly between 0 and 1.
    ValueError
        If *sprite_ids* is empty.

    Examples
    --------
    >>> ids = [str(i) for i in range(100)]
    >>> train, val = split_dataset(ids, validation_ratio=0.2, seed=0)
    >>> len(val)
    20
    >>> len(train)
    80
    """
    if not (0 < validation_ratio < 1):
        raise ValueError(f"validation_ratio must be in (0, 1), got {validation_ratio!r}")
    if not sprite_ids:
        raise ValueError("sprite_ids must not be empty")

    rng = random.Random(seed)
    shuffled = list(sprite_ids)
    rng.shuffle(shuffled)

    n_val = max(1, round(len(shuffled) * validation_ratio))
    val_ids = shuffled[:n_val]
    train_ids = shuffled[n_val:]
    return train_ids, val_ids


def split_by_genre(
    sprites: list[dict],
    validation_ratio: float = 0.10,
    seed: int = 42,
) -> tuple[list[str], list[str]]:
    """Stratified train/val split that preserves ``genre_hint`` distribution.

    Each genre bucket is independently shuffled and split at *validation_ratio*
    so that every genre class appears in both the training and validation sets
    at approximately the same proportion as in the original data.

    Parameters
    ----------
    sprites:
        List of provenance dicts.  Each dict must contain at least a
        ``"sprite_id"`` key.  The ``"genre_hint"`` key is used for
        stratification; sprites missing this key are grouped under the
        implicit bucket ``""`` (empty string).
    validation_ratio:
        Fraction of each genre bucket to place in validation.  Default 0.10.
    seed:
        RNG seed for reproducibility.

    Returns
    -------
    tuple[list[str], list[str]]
        ``(train_ids, val_ids)`` as flat lists of sprite ID strings.

    Raises
    ------
    ValueError
        If *sprites* is empty or *validation_ratio* is out of range.

    Notes
    -----
    Genre buckets with only one sprite always go to *training* to avoid
    producing an empty training set for that genre.

    Examples
    --------
    >>> sprites = [{"sprite_id": f"s{i}", "genre_hint": "fantasy"} for i in range(10)]
    >>> sprites += [{"sprite_id": f"r{i}", "genre_hint": "rpg"} for i in range(5)]
    >>> train, val = split_by_genre(sprites, validation_ratio=0.2)
    >>> len(val)
    3
    """
    if not (0 < validation_ratio < 1):
        raise ValueError(f"validation_ratio must be in (0, 1), got {validation_ratio!r}")
    if not sprites:
        raise ValueError("sprites list must not be empty")

    rng = random.Random(seed)

    # Group sprite IDs by genre
    buckets: dict[str, list[str]] = defaultdict(list)
    for sprite in sprites:
        genre = sprite.get("genre_hint", "") or ""
        buckets[genre].append(sprite["sprite_id"])

    train_ids: list[str] = []
    val_ids: list[str] = []

    for genre, ids in sorted(buckets.items()):  # sorted for determinism
        rng.shuffle(ids)
        if len(ids) == 1:
            # Cannot split a singleton; always goes to train
            train_ids.extend(ids)
            continue
        n_val = max(1, round(len(ids) * validation_ratio))
        val_ids.extend(ids[:n_val])
        train_ids.extend(ids[n_val:])

    return train_ids, val_ids


# ---------------------------------------------------------------------------
# Manifest I/O
# ---------------------------------------------------------------------------

def write_split_manifest(
    train_ids: list[str],
    val_ids: list[str],
    output_dir: str | Path,
) -> None:
    """Write ``train.json`` and ``val.json`` to *output_dir*.

    Each file contains a JSON array of sprite ID strings, written with
    2-space indentation for readability.  The output directory is created
    if it does not already exist.

    Parameters
    ----------
    train_ids:
        List of sprite IDs assigned to the training split.
    val_ids:
        List of sprite IDs assigned to the validation split.
    output_dir:
        Directory path where the two JSON files will be written.

    Side Effects
    ------------
    Creates *output_dir* (and any missing parents) if absent.
    Overwrites any existing ``train.json`` / ``val.json`` in that directory.

    Examples
    --------
    ::

        write_split_manifest(train, val, "data/splits/v1/")
        # → data/splits/v1/train.json
        # → data/splits/v1/val.json
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "train.json").write_text(
        json.dumps(train_ids, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output_dir / "val.json").write_text(
        json.dumps(val_ids, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def load_split(split_path: str | Path) -> list[str]:
    """Load a list of sprite IDs from a split JSON file.

    Parameters
    ----------
    split_path:
        Path to a ``train.json`` or ``val.json`` file produced by
        :func:`write_split_manifest`.

    Returns
    -------
    list[str]
        Ordered list of sprite ID strings.

    Raises
    ------
    FileNotFoundError
        If *split_path* does not exist.
    json.JSONDecodeError
        If the file contains malformed JSON.
    TypeError
        If the JSON root value is not a list.
    """
    split_path = Path(split_path)
    if not split_path.exists():
        raise FileNotFoundError(f"Split file not found: {split_path}")
    data = json.loads(split_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise TypeError(f"Expected a JSON array in {split_path}, got {type(data).__name__}")
    return data


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """Command-line interface for dataset splitting.

    Sub-commands
    ------------
    split
        Load a flat manifest JSON (list of sprite ID strings) and write
        train/val splits to an output directory.
    split-genre
        Load a provenance manifest JSON (list of dicts with ``sprite_id``
        and ``genre_hint``) and perform a stratified split.
    show
        Print the IDs in an existing split file.

    Examples
    --------
    ::

        # Simple split from a flat ID list
        python splitter.py split --ids ids.json --output-dir splits/ --ratio 0.1

        # Stratified split from a provenance manifest
        python splitter.py split-genre --manifest manifest.json --output-dir splits/

        # Inspect a split
        python splitter.py show --split splits/val.json
    """
    parser = argparse.ArgumentParser(
        prog="splitter",
        description="AM Pixel — dataset train/val split utilities",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- split ---
    p_split = sub.add_parser("split", help="Simple deterministic split of a flat ID list")
    p_split.add_argument("--ids", required=True,
                         help="JSON file containing a list of sprite ID strings")
    p_split.add_argument("--output-dir", required=True, help="Directory for train.json / val.json")
    p_split.add_argument("--ratio", type=float, default=0.10,
                         help="Validation fraction (default: 0.10)")
    p_split.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")

    # --- split-genre ---
    p_genre = sub.add_parser("split-genre", help="Stratified split by genre_hint field")
    p_genre.add_argument("--manifest", required=True,
                         help="JSON manifest (list of provenance dicts)")
    p_genre.add_argument("--output-dir", required=True,
                         help="Directory for train.json / val.json")
    p_genre.add_argument("--ratio", type=float, default=0.10,
                         help="Validation fraction per genre (default: 0.10)")
    p_genre.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")

    # --- show ---
    p_show = sub.add_parser("show", help="Display sprite IDs in a split file")
    p_show.add_argument("--split", required=True, help="Path to train.json or val.json")

    args = parser.parse_args()

    if args.command == "split":
        raw = json.loads(Path(args.ids).read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            print("[splitter] ERROR: --ids file must contain a JSON array.", file=sys.stderr)
            sys.exit(1)
        train, val = split_dataset(raw, validation_ratio=args.ratio, seed=args.seed)
        write_split_manifest(train, val, args.output_dir)
        print(f"[splitter] Split complete → {len(train)} train, {len(val)} val")
        print(f"           Written to: {args.output_dir}/train.json & val.json")

    elif args.command == "split-genre":
        sprites = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        if not isinstance(sprites, list):
            print("[splitter] ERROR: --manifest must be a JSON array of dicts.", file=sys.stderr)
            sys.exit(1)
        train, val = split_by_genre(sprites, validation_ratio=args.ratio, seed=args.seed)
        write_split_manifest(train, val, args.output_dir)

        # Count genres for summary
        from collections import Counter
        genre_counts: Counter = Counter(s.get("genre_hint", "") for s in sprites)
        print(f"[splitter] Stratified split — genres: {dict(genre_counts)}")
        print(f"           {len(train)} train, {len(val)} val")
        print(f"           Written to: {args.output_dir}/train.json & val.json")

    elif args.command == "show":
        ids = load_split(args.split)
        print(f"[splitter] {len(ids)} sprite(s) in {args.split}:")
        for sid in ids:
            print(f"  {sid}")


if __name__ == "__main__":
    main()
