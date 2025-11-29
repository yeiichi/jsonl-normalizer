#!/usr/bin/env python3
"""
JSONL Concatenator for jsonl-normalizer.

Usage examples:
    jsonl-concat
    jsonl-concat norm_jsonl/
    jsonl-concat norm_jsonl/ out.jsonl
    jsonl-concat --no-dedupe
    jsonl-concat --verbose
"""

import argparse
import hashlib
from pathlib import Path


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def concat_jsonl(
        source_dir: Path,
        output_file: Path,
        dedupe: bool = True,
        verbose: bool = True,
) -> None:
    files = sorted(source_dir.glob("normalized_*.jsonl"))
    if not files:
        print(f"[WARN] No normalized_*.jsonl found in {source_dir}")
        return

    if verbose:
        print(f"[INFO] Input directory : {source_dir}")
        print(f"[INFO] Output file     : {output_file}")
        print(f"[INFO] Files detected  : {len(files)}")

    seen: set[str] = set()
    count_in = 0
    count_out = 0

    with output_file.open("w", encoding="utf-8") as fout:
        for fp in files:
            text = fp.read_text(encoding="utf-8").strip()
            if not text:
                continue

            count_in += 1
            digest = sha256_hex(text)

            if dedupe and digest in seen:
                if verbose:
                    print(f"[SKIP] Duplicate: {fp.name}")
                continue

            seen.add(digest)
            fout.write(text + "\n")
            count_out += 1

    if verbose:
        print("\n[RESULT]")
        print(f"  Lines read   : {count_in}")
        print(f"  Lines written: {count_out}")
        print(f"  Dedupe       : {dedupe}")
        print(f"  Output path  : {output_file.resolve()}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jsonl-concat",
        description="Concatenate normalized_*.jsonl files into a single multi-line JSONL (BigQuery-friendly).",
    )

    p.add_argument(
        "source_dir",
        nargs="?",
        default="norm_jsonl",
        help="Directory containing normalized_*.jsonl files (default: norm_jsonl).",
    )
    p.add_argument(
        "output_file",
        nargs="?",
        default="combined.jsonl",
        help="Output JSONL file path (default: combined.jsonl).",
    )
    p.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Disable deduplication (default: dedupe enabled).",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    output_file = Path(args.output_file)
    dedupe = not args.no_dedupe
    verbose = args.verbose

    if verbose and output_file.suffix.lower() not in {".jsonl", ".ndjson"}:
        print(f"[WARN] Output file '{output_file.name}' does not use .jsonl or .ndjson. Continuing.")

    concat_jsonl(
        source_dir=source_dir,
        output_file=output_file,
        dedupe=dedupe,
        verbose=verbose,
    )

    if __name__ == "__main__":
        main()


if __name__ == "__main__":
    main()
