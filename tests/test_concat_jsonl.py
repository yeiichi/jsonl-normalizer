import json

from jsonl_normalizer.tools.concat_jsonl import concat_jsonl


def test_concat_simple(tmp_path):
    # Prepare a fake norm_jsonl directory with two different JSONL files
    src_dir = tmp_path / "norm_jsonl"
    src_dir.mkdir()

    f1 = src_dir / "normalized_a.jsonl"
    f2 = src_dir / "normalized_b.jsonl"

    obj1 = {"id": 1, "value": "foo"}
    obj2 = {"id": 2, "value": "bar"}

    f1.write_text(json.dumps(obj1, ensure_ascii=False) + "\n", encoding="utf-8")
    f2.write_text(json.dumps(obj2, ensure_ascii=False) + "\n", encoding="utf-8")

    out_file = tmp_path / "combined.jsonl"

    concat_jsonl(source_dir=src_dir, output_file=out_file, dedupe=True, verbose=False)

    assert out_file.is_file()

    lines = out_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    parsed = [json.loads(line) for line in lines]
    assert obj1 in parsed
    assert obj2 in parsed


def test_concat_dedupe(tmp_path):
    # Two files with the same JSON content -> should dedupe to one line
    src_dir = tmp_path / "norm_jsonl"
    src_dir.mkdir()

    obj = {"id": 1, "value": "dup"}

    for name in ("normalized_a.jsonl", "normalized_b.jsonl"):
        (src_dir / name).write_text(json.dumps(obj, ensure_ascii=False) + "\n", encoding="utf-8")

    out_file = tmp_path / "combined.jsonl"

    concat_jsonl(source_dir=src_dir, output_file=out_file, dedupe=True, verbose=False)

    lines = out_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == obj


def test_concat_no_files(tmp_path, capsys):
    # Empty directory: should warn and not crash
    src_dir = tmp_path / "norm_jsonl"
    src_dir.mkdir()

    out_file = tmp_path / "combined.jsonl"

    concat_jsonl(source_dir=src_dir, output_file=out_file, dedupe=True, verbose=True)
    captured = capsys.readouterr()

    # We expect a warning about no files
    assert "[WARN] No normalized_*.jsonl" in captured.out

    # Output file may or may not exist, but should not contain data
    if out_file.exists():
        assert out_file.read_text(encoding="utf-8").strip() == ""


import sys
from jsonl_normalizer.tools import concat_jsonl as concat_mod


def test_main_suffix_warn(tmp_path, capsys, monkeypatch):
    src_dir = tmp_path / "norm_jsonl"
    src_dir.mkdir()
    # one simple file
    f = src_dir / "normalized_a.jsonl"
    f.write_text('{"id": 1}\n', encoding="utf-8")

    out_file = tmp_path / "out.json"  # intentionally non-.jsonl
    argv = ["jsonl-concat", "--verbose", str(src_dir), str(out_file)]
    monkeypatch.setattr(sys, "argv", argv)

    concat_mod.main()
    captured = capsys.readouterr()

    # Check that the warning was printed
    assert "does not use .jsonl or .ndjson" in captured.out

    # And the file was still created and contains one line
    lines = out_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
