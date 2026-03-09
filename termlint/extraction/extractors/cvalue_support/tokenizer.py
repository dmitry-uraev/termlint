"""Tokenization helpers for the C-Value extractor."""

from __future__ import annotations

import re
from typing import List

from termlint.extraction.extractors.cvalue_support.config import STOP_WORDS, TOKEN_PATTERN
from termlint.extraction.extractors.cvalue_support.types import TokenInfo


def tokenize_with_spacy(nlp, text: str) -> List[TokenInfo]:
    """Tokenize text with spaCy and preserve sentence boundaries.

    All non-space tokens are returned. Candidate filtering is intentionally
    deferred to the candidate generator stage.
    """
    doc = nlp(text)
    tokens: List[TokenInfo] = []

    for sent_id, sent in enumerate(doc.sents):
        for token in sent:
            if token.is_space:
                continue

            tokens.append(
                TokenInfo(
                    token=token.text,
                    lemma=token.lemma_.lower(),
                    pos=token.pos_,
                    char_start=int(token.idx),
                    char_end=int(token.idx + len(token.text)),
                    sent_id=sent_id,
                    is_stop=bool(token.is_stop),
                    is_punct=bool(token.is_punct),
                )
            )

    return tokens


def tokenize_with_regex(text: str) -> List[TokenInfo]:
    """Tokenize text with a lightweight regex tokenizer.

    This tokenizer is used as a fallback when spaCy is unavailable or disabled.
    Sentence boundaries are inferred from punctuation marks.
    """
    tokens: List[TokenInfo] = []
    sent_id = 0

    for match in re.finditer(TOKEN_PATTERN, text):
        value = match.group(0)

        if re.fullmatch(r"[.!?]+", value):
            sent_id += 1
            continue

        tokens.append(
            TokenInfo(
                token=value,
                lemma=value.lower(),
                pos=None,
                char_start=match.start(),
                char_end=match.end(),
                sent_id=sent_id,
                is_stop=value.lower() in STOP_WORDS,
                is_punct=False,
            )
        )

    return tokens
