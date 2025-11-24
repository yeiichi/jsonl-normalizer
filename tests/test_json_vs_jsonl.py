import json
from io import StringIO

import pytest

from jsonl_normalizer.core import normalize_jsonl, NormalizationStats


def _split_jsonl(s: str):
    """Helper: parse JSONL string into list[dict]."""
    lines = [ln for ln in s.splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines]


def test_jsonl_basic_path_io(tmp_path):
    """JSONL input with valid/invalid lines via real files."""
    input_text = '\n'.join(
        [
            '{"id": 1, "name": "foo"}',
            'not a json line',
            '{"id": 2, "name": "bar"}',
            '',
        ]
    )

    input_file = tmp_path / "input.jsonl"
    output_file = tmp_path / "output.jsonl"
    discarded_file = tmp_path / "discarded.jsonl"

    input_file.write_text(input_text, encoding="utf-8")

    stats = normalize_jsonl(
        input_file,
        output_file,
        discarded_file,
        dedupe=False,
    )

    # Output: two valid dict records
    out_records = _split_jsonl(output_file.read_text(encoding="utf-8"))
    assert len(out_records) == 2
    assert out_records[0]["id"] == 1
    assert out_records[1]["id"] == 2

    # Discarded: one decode error line
    discarded_records = _split_jsonl(discarded_file.read_text(encoding="utf-8"))
    assert len(discarded_records) == 1
    assert discarded_records[0]["reason"] == "json_decode_error"

    # Stats sanity
    assert isinstance(stats, NormalizationStats)
    assert stats.normalized_seen == 2
    assert stats.written == 2
    assert stats.discarded_count == 1
    assert stats.duplicates_skipped == 0


def test_jsonl_dedupe_with_stringio():
    """JSONL input via StringIO, with duplicate dict rows and dedupe=True."""
    src = StringIO(
        '\n'.join(
            [
                '{"id": 1, "name": "foo"}',
                '{"id": 1, "name": "foo"}',
                '{"id": 2, "name": "bar"}',
            ]
        )
    )
    out = StringIO()
    discarded = StringIO()

    stats = normalize_jsonl(src, out, discarded, dedupe=True)

    out_records = _split_jsonl(out.getvalue())
    discarded_records = _split_jsonl(discarded.getvalue())

    # We had 3 valid dict records, but one is a duplicate.
    assert len(out_records) == 2
    ids = sorted(r["id"] for r in out_records)
    assert ids == [1, 2]

    assert len(discarded_records) == 0

    assert stats.normalized_seen == 3
    assert stats.written == 2
    assert stats.duplicates_skipped == 1
    assert stats.discarded_count == 0


def test_classic_json_object_stringio():
    """Classic JSON (single dict) via StringIO should yield one JSONL record."""
    src = StringIO(
        json.dumps(
            {
                "id": 10,
                "name": "classic",
            },
            indent=2,
        )
    )
    out = StringIO()
    discarded = StringIO()

    stats = normalize_jsonl(src, out, discarded, dedupe=False)

    out_records = _split_jsonl(out.getvalue())
    discarded_records = _split_jsonl(discarded.getvalue())

    assert len(out_records) == 1
    assert out_records[0]["id"] == 10
    assert out_records[0]["name"] == "classic"

    assert len(discarded_records) == 0

    assert stats.normalized_seen == 1
    assert stats.written == 1
    assert stats.discarded_count == 0
    assert stats.duplicates_skipped == 0


def test_classic_json_list_mixed():
    """
    Classic JSON: list of mixed items.

    - dict elements should be kept
    - non-dict elements should be logged to discarded
    """
    src_obj = [
        {"id": 1, "kind": "keep"},
        123,
        {"id": 2, "kind": "keep"},
        "oops",
    ]
    src = StringIO(json.dumps(src_obj, indent=2))
    out = StringIO()
    discarded = StringIO()

    stats = normalize_jsonl(src, out, discarded, dedupe=False)

    out_records = _split_jsonl(out.getvalue())
    discarded_records = _split_jsonl(discarded.getvalue())

    # We expect two dict records in the output
    assert len(out_records) == 2
    ids = sorted(r["id"] for r in out_records)
    assert ids == [1, 2]

    # Two non-dict elements (123 and "oops") logged as discarded
    assert len(discarded_records) == 2
    reasons = {rec["reason"] for rec in discarded_records}
    assert reasons == {"non-dict element in list"}

    # Stats
    assert stats.normalized_seen == 2
    assert stats.written == 2
    assert stats.discarded_count == 2
    assert stats.duplicates_skipped == 0


def test_empty_input():
    """Empty input should produce no output and an empty discarded file."""
    src = StringIO("")  # completely empty
    out = StringIO()
    discarded = StringIO()

    stats = normalize_jsonl(src, out, discarded, dedupe=True)

    assert out.getvalue() == ""
    assert discarded.getvalue() == ""

    assert stats.normalized_seen == 0
    assert stats.written == 0
    assert stats.discarded_count == 0
    assert stats.duplicates_skipped == 0


def test_discarded_output_is_jsonl():
    """
    Ensure discarded_path also accepts file-like objects and produces valid JSONL.
    """
    # One good dict line + one broken line
    src = StringIO(
        '\n'.join(
            [
                '{"id": 1, "name": "ok"}',
                'not-json',
            ]
        )
    )
    out = StringIO()
    discarded = StringIO()

    stats = normalize_jsonl(src, out, discarded, dedupe=False)

    # Output: only one valid dict
    out_records = _split_jsonl(out.getvalue())
    assert len(out_records) == 1
    assert out_records[0]["id"] == 1

    # Discarded: one json_decode_error record
    discarded_records = _split_jsonl(discarded.getvalue())
    assert len(discarded_records) == 1
    rec = discarded_records[0]
    assert rec["reason"] == "json_decode_error"
    assert "raw" in rec

    assert stats.normalized_seen == 1
    assert stats.written == 1
    assert stats.discarded_count == 1
