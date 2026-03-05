"""Helpers for glossary conversion and merge."""

import re
from hashlib import sha1


_MULTISPACE_RE = re.compile(r"\s+")


def canonical_term(value: str) -> str:
    """Build a canonical term key used for dedupe/match."""
    text = value.lower().strip().replace("ё", "е")
    text = _MULTISPACE_RE.sub(" ", text)
    text = text.strip(".,;:!?()[]{}\"'`")
    return text


def stable_id(namespace: str, canonical_key: str, used_ids: set[str]) -> str:
    """Build deterministic ID from canonical term; extend hash on collisions."""
    digest = sha1(canonical_key.encode("utf-8")).hexdigest()
    for length in (10, 14, 20, 40):
        candidate = f"{namespace}:{digest[:length]}"
        if candidate not in used_ids:
            return candidate
    return f"{namespace}:{digest}"
