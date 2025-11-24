from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO, Union
from contextlib import contextmanager


# ---------------------------------------------------------------------------
# Type aliases for flexible I/O
# ---------------------------------------------------------------------------

PathLike = Union[str, Path]
ReaderLike = Union[PathLike, TextIO]
WriterLike = Union[PathLike, TextIO]


@contextmanager
def _as_text_reader(source: ReaderLike, encoding: str) -> TextIO:
    """
    Accept either a path-like or an already-open text file object.

    - If ``source`` is ``str``/``Path`` -> open it in text mode and close on exit.
    - Otherwise assume it's a text file-like object and just yield it.
    """
    if isinstance(source, (str, Path)):
        f = Path(source).open("r", encoding=encoding)
        try:
            yield f
        finally:
            f.close()
    else:
        # Assume it's already a text-mode file-like object (e.g. StringIO)
        yield source  # type: ignore[return-value]


@contextmanager
def _as_text_writer(target: WriterLike, encoding: str) -> TextIO:
    """
    Accept either a path-like or an already-open text file object.

    - If ``target`` is ``str``/``Path`` -> open it in text mode and close on exit.
    - Otherwise assume it's a text file-like object and just yield it.
    """
    if isinstance(target, (str, Path)):
        f = Path(target).open("w", encoding=encoding)
        try:
            yield f
        finally:
            f.close()
    else:
        # Assume it's already a text-mode file-like object
        yield target  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Stats + helpers
# ---------------------------------------------------------------------------


@dataclass
class NormalizationStats:
    """Summary statistics for a normalization run."""

    normalized_seen: int = 0
    written: int = 0
    duplicates_skipped: int = 0
    discarded_count: int = 0


def stable_hash(obj: dict) -> str:
    """
    Compute a stable SHA-256 hash for a JSON-able dict.

    We canonicalize the dict by:

    * Sorting keys
    * Using compact separators
    * Keeping non-ASCII characters as-is (ensure_ascii=False)

    so that semantically equal dicts yield the same hash string.
    """
    canonical = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_line(obj: Any, lineno: int, discarded: list[dict]) -> list[dict]:
    """
    Normalize a single parsed JSON value into a list of dicts.

    Non-dict content is recorded into ``discarded`` with metadata.

    Rules:
      - dict          -> keep as one record
      - list[dict, *] -> keep dict elements, discard others
      - anything else -> discard
    """
    out: list[dict] = []

    # Case 1: top-level dict: keep as-is
    if isinstance(obj, dict):
        out.append(obj)

    # Case 2: top-level list: extract dicts, log junk
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            if isinstance(item, dict):
                out.append(item)
            else:
                discarded.append(
                    {
                        "line": lineno,
                        "index": idx,
                        "type": type(item).__name__,
                        "value": item,
                        "reason": "non-dict element in list",
                    }
                )

    # Case 3: everything else -> discard with reason
    else:
        discarded.append(
            {
                "line": lineno,
                "type": type(obj).__name__,
                "value": obj,
                "reason": "non-dict top-level value",
            }
        )

    return out


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------


def normalize_jsonl(
    input_path: ReaderLike,
    output_path: WriterLike,
    discarded_path: WriterLike,
    *,
    dedupe: bool = False,
    encoding: str = "utf-8",
) -> NormalizationStats:
    """
    Normalize JSONL *or* classic JSON into dict-only JSONL, optionally deduplicated.

    Parameters
    ----------
    input_path:
        Source to read from. Can be:

        * path-like (str or Path) pointing to a file containing JSONL or JSON
        * a text-mode file-like object (e.g. io.StringIO, already-open file)

    output_path:
        Destination for normalized dict-only JSONL. Can be path-like or
        text-mode file-like.

    discarded_path:
        Destination for discarded items (one JSON object per line), path-like or
        text-mode file-like.

    dedupe:
        If True, drop duplicates using a canonical SHA-256 hash of each record.

    encoding:
        Text encoding to use when opening path-like inputs/outputs.

    Returns
    -------
    NormalizationStats
        Aggregate statistics about the normalization run.
    """
    stats = NormalizationStats()
    discarded: list[dict] = []
    seen_hashes: set[str] = set()

    # --- Read input once (works for both paths and file-like objects) ---
    with _as_text_reader(input_path, encoding) as fin:
        content = fin.read()

    if not content.strip():
        # Empty input: nothing to do, but still write an empty discarded file.
        normalized_records: list[dict] = []
    else:
        # Try to parse as a single classic JSON document first.
        try:
            obj = json.loads(content)
        except json.JSONDecodeError:
            # Fall back: treat as JSONL (one JSON per non-empty line)
            normalized_records = []
            for lineno, line in enumerate(content.splitlines(), start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    line_obj = json.loads(line)
                except Exception as e:  # pragma: no cover - defensive
                    discarded.append(
                        {
                            "line": lineno,
                            "raw": line,
                            "error": repr(e),
                            "reason": "json_decode_error",
                        }
                    )
                    continue

                normalized_records.extend(
                    normalize_line(line_obj, lineno, discarded)
                )
        else:
            # Parsed as a single classic JSON value (dict, list, etc.).
            # Treat the whole document as "line 1" for metadata purposes.
            normalized_records = normalize_line(obj, lineno=1, discarded=discarded)

    # --- Write normalized records, with optional dedupe ---
    with _as_text_writer(output_path, encoding) as fout:
        for rec in normalized_records:
            stats.normalized_seen += 1

            if dedupe:
                h = stable_hash(rec)
                if h in seen_hashes:
                    stats.duplicates_skipped += 1
                    continue
                seen_hashes.add(h)

            json.dump(rec, fout, ensure_ascii=False)
            fout.write("\n")
            stats.written += 1

    # --- Write discarded items ---
    with _as_text_writer(discarded_path, encoding) as fdisc:
        for item in discarded:
            json.dump(item, fdisc, ensure_ascii=False)
            fdisc.write("\n")

    stats.discarded_count = len(discarded)
    return stats
