# jsonl-normalizer

[![PyPI version](https://img.shields.io/pypi/v/jsonl-normalizer.svg)](https://pypi.org/project/jsonl-normalizer/)
![Python versions](https://img.shields.io/pypi/pyversions/jsonl-normalizer.svg)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A fast, fault-tolerant tool that normalizes messy JSONL files into clean, dict-only, BigQuery-friendly JSONL. Supports discard logging, SHA-256 deduplication, JSONL concatenation, and mixed-type top-level lines (dicts, lists, strings, numbers).

---

## 🚀 Features

### Normalization
- Normalize any JSONL file  
  - Accepts dicts, lists, numbers, strings, malformed lines  
  - Extracts dicts from lists  
  - Logs non-dict elements instead of failing

- BigQuery-friendly output  
  Ensures **one JSON object per line**.

- Robust error handling  
  - Malformed JSON → logged  
  - Non-dict top-level values → logged  
  - Mixed lists → dicts kept, junk discarded

- Optional SHA-256 deduplication  
  Canonical JSON hashing removes duplicate objects across large files.

- Zero dependencies  
  Pure standard library. Fast and lightweight.

### NEW (v0.2.0): JSONL Concatenation
- Combine many `normalized_*.jsonl` files into one newline-delimited JSONL
- Perfect for BigQuery (`NEWLINE_DELIMITED_JSON`)
- Optional dedupe via SHA-256
- Gentle warnings for non-standard output filenames
- Clean argparse-based CLI (`jsonl-concat`)

---

## 📦 Installation

```bash
pip install jsonl-normalizer
```

Development install:

```bash
pip install -e .
```

---

# 🖥️ CLI Usage

## 1. Normalize JSONL

Normalize a JSONL file:

```bash
jsonl-normalize input.jsonl
```

Produces:

```
normalized.jsonl   # clean dict-only output
discarded.jsonl    # log of malformed or discarded items
```

Enable deduplication:

```bash
jsonl-normalize input.jsonl --dedupe
```

Specify custom output:

```bash
jsonl-normalize input.jsonl --output clean.jsonl --discarded junk.jsonl
```

---

# 🔗 NEW: `jsonl-concat` — JSONL Concatenation Tool

`jsonl-concat` concatenates multiple normalized JSONL files into a single multi-line JSONL file.

This is ideal when your workflow produces many files such as:

```text
norm_jsonl/
  normalized_0044a4b1d5099e2a.jsonl
  normalized_007b2d5c01abc0b9.jsonl
  normalized_02231d6de9a07833.jsonl
  ...
```

Combine them into one BigQuery-friendly file:

```bash
jsonl-concat
```

Default behavior is equivalent to:

```bash
jsonl-concat norm_jsonl/ combined.jsonl
```

### Features
- Reads all `normalized_*.jsonl` under the given directory  
- Writes **one JSON object per line**  
- Optional SHA-256 dedupe (`--no-dedupe` to disable)
- Verbose mode (`--verbose`)  
- Gentle suffix warning when output file is not `.jsonl`/`.ndjson`  

### Examples

Use defaults:

```bash
jsonl-concat
```

Explicit directory and output:

```bash
jsonl-concat norm_jsonl/ final.jsonl
```

Verbose output:

```bash
jsonl-concat --verbose norm_jsonl/ combined.jsonl
```

Disable deduplication:

```bash
jsonl-concat --no-dedupe norm_jsonl/ combined.jsonl
```

If verbose and output filename is non-standard:

```
[WARN] Output file 'out.json' does not use .jsonl or .ndjson. Continuing.
```

---

# 📄 Example (Normalization)

### Input (`mixed.jsonl`)

```json
{"a": 1, "b": 2}
[{"a": 2}, [7]]
"just a string"
```

### Output: `normalized.jsonl`

```json
{"a": 1, "b": 2}
{"a": 2}
```

### Output: `discarded.jsonl`

```json
{"line": 2, "index": 1, "type": "list", "value": [7], "reason": "non-dict element in list"}
{"line": 3, "type": "str", "value": "just a string", "reason": "top-level value is not dict or list"}
```

---

# 🧪 Library Usage

```python
from pathlib import Path
from jsonl_normalizer import normalize_jsonl

stats = normalize_jsonl(
    input_path=Path("input.jsonl"),
    output_path=Path("normalized.jsonl"),
    discarded_path=Path("discarded.jsonl"),
    dedupe=True,
)

print(stats)
```

---

# ❓ Why jsonl-normalizer?

Real-world JSONL is messy:

- LLMs output arrays or malformed fragments  
- Excel corrupts JSON strings  
- Some APIs return non-dict top-level structures  
- Data lakes accumulate junk  
- BigQuery requires **strict dict-per-line JSONL**  
- ETL pipelines fail on partial corruption  

`jsonl-normalizer` fixes these problems by:

- Normalizing structure  
- Logging all junk transparently  
- Keeping valid dicts only  
- Providing optional dedupe mode  
- Producing **warehouse-ready JSONL**

---

# 🧹 Deduplication

When `--dedupe` is enabled:

- Each object is canonicalized (sorted keys, compact JSON)  
- Hashed using SHA-256  
- Duplicates are skipped automatically

Example:

```
Normalized records seen: 200
Unique records written: 173
Duplicates skipped: 27
Discarded items logged: 12 → discarded.jsonl
```

---

# 🧪 Testing

```bash
pip install -e .
pip install pytest
pytest
```

---

# 🤝 Contributing

Pull requests are welcome. Please ensure:

- Tests pass  
- Code follows PEP 8  
- Changes remain backward compatible  

---

# 📄 License

MIT License. See `LICENSE` for details.
