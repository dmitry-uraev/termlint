"""Shared types for the C-Value extractor."""

from typing import TypedDict, Optional


class TokenInfo(TypedDict):
    """Normalized token representation used by candidate generators."""

    token: str
    lemma: str
    pos: Optional[str]
    char_start: int
    char_end: int
    sent_id: int
    is_stop: bool
    is_punct: bool
