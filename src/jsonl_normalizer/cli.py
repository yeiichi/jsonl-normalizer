from __future__ import annotations

import argparse
from pathlib import Path

from .core import normalize_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize mixed JSONL (dicts/lists) into dict-only JSONL. "
            "Optionally deduplicate records using SHA-256 over canonical JSON."
        )
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input JSONL file (mixed types).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("normalized.jsonl"),
        help="Output JSONL file with dict-only records (default: normalized.jsonl).",
    )
    parser.add_argument(
        "--discarded",
        type=Path,
        default=Path("discarded.jsonl"),
        help="JSONL file for discarded non-dict/malformed content (default: discarded.jsonl).",
    )
    parser.add_argument(
        "--dedupe",
        action="store_true",
        help="Enable SHA-256-based deduplication of normalized records.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    stats = normalize_jsonl(
        input_path=args.input,
        output_path=args.output,
        discarded_path=args.discarded,
        dedupe=args.dedupe,
    )

    # Simple human-readable summary
    if args.dedupe:
        print(f"Normalized records seen: {stats.normalized_seen}")
        print(f"Unique records written: {stats.written}")
        print(f"Duplicates skipped: {stats.duplicates_skipped}")
    else:
        print(f"Normalized records written: {stats.written} (dedupe disabled)")

    print(f"Discarded items logged: {stats.discarded_count} -> {args.discarded}")
