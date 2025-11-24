"""
jsonl_normalizer
=================

Tiny helper library to normalize JSON / JSONL into a clean dict-only JSONL stream.

Public API
----------

- ``normalize_jsonl``:
    Core function that accepts JSONL *or* classic JSON (dict / list),
    optional de-duplication, and flexible I/O (paths or file-like objects).

- ``NormalizationStats``:
    Dataclass summarizing what happened during a normalization run.

Typical usage
-------------

.. code-block:: python

    from jsonl_normalizer import normalize_jsonl

    stats = normalize_jsonl(
        "input.jsonl",
        "output.normalized.jsonl",
        "discarded.jsonl",
        dedupe=True,
    )
"""

from __future__ import annotations

from .core import NormalizationStats, normalize_jsonl

try:  # Python 3.8+
    from importlib.metadata import PackageNotFoundError, version
except ImportError:  # pragma: no cover - for very old Python only
    from importlib_metadata import PackageNotFoundError, version  # type: ignore[assignment]


try:
    # When installed as a package, this will reflect the version in pyproject.toml
    __version__ = version("jsonl_normalizer")
except PackageNotFoundError:  # pragma: no cover - during local dev without install
    # Fallback for editable / source-only usage
    __version__ = "0.0.0"

__all__ = [
    "normalize_jsonl",
    "NormalizationStats",
    "__version__",
]
