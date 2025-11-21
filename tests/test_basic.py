from __future__ import annotations

import json
from pathlib import Path

from jsonl_normalizer import normalize_jsonl


def test_basic_normalization(tmp_path: Path) -> None:
    # Create a tiny mixed JSONL sample
    input_path = tmp_path / "input.jsonl"
    output_path = tmp_path / "normalized.jsonl"
    discarded_path = tmp_path / "discarded.jsonl"

    lines = [
        '{"a": 1, "b": 2}\n',
        '[{"a": 2}, [7]]\n',
        '"just a string"\n',
    ]
    input_path.write_text("".join(lines), encoding="utf-8")

    stats = normalize_jsonl(
        input_path=input_path,
        output_path=output_path,
        discarded_path=discarded_path,
        dedupe=False,
    )

    # We expect 2 dict records: {"a":1,"b":2} and {"a":2}
    out_lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(out_lines) == 2

    objs = [json.loads(l) for l in out_lines]
    assert {"a": 1, "b": 2} in objs
    assert {"a": 2} in objs

    # Discarded: the [7] element + the top-level string
    assert stats.discarded_count == 2
