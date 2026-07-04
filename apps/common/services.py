from __future__ import annotations

import hashlib
import re


def content_hash(text: str) -> str:
    """sha256(normalize(text)).hexdigest() — normalize = lower + strip + collapse whitespace."""
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

