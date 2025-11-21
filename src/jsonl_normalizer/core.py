from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


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
    Uses sorted keys and compact separators for canonical representation.
    """
    canonical = json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_line(obj: Any, lineno: int, discarded: list[dict]) -> list[dict]:
    """
    Normalize a single parsed JSON value into a list of dicts.
    Non-dict content is recorded into `discarded` with metadata.
    Rules:
      - dict         -> keep as one record
      - list[dict,*] -> keep dict elements, discard others
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
                "reason": "top-level value is not dict or list",
            }
        )

    return out


def normalize_jsonl(
    input_path: Path,
    output_path: Path,
    discarded_path: Path,
    *,
    dedupe: bool = False,
    encoding: str = "utf-8",
) -> NormalizationStats:
    """
    Normalize a JSONL file into dict-only JSONL, optionally deduplicated.

    - input_path:    JSONL file to read (may contain dicts, lists, other)
    - output_path:   normalized dict-only JSONL
    - discarded_path: JSONL log of discarded items, malformed lines, etc.
    - dedupe:        if True, use SHA-256 over canonical JSON to drop duplicates

    Returns:
        NormalizationStats with counts.
    """
    stats = NormalizationStats()
    discarded: list[dict] = []
    seen_hashes: set[str] = set()

    with input_path.open("r", encoding=encoding) as fin, \
            output_path.open("w", encoding=encoding) as fout:

        for lineno, line in enumerate(fin, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except Exception as e:
                discarded.append(
                    {
                        "line": lineno,
                        "raw": line,
                        "error": repr(e),
                        "reason": "json_decode_error",
                    }
                )
                continue

            normalized = normalize_line(obj, lineno, discarded)

            for rec in normalized:
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

    # Write discarded items
    with discarded_path.open("w", encoding=encoding) as fdisc:
        for item in discarded:
            json.dump(item, fdisc, ensure_ascii=False)
            fdisc.write("\n")

    stats.discarded_count = len(discarded)
    return stats
