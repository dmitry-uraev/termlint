"""Candidate generation strategies for the C-Value extractor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from termlint.extraction.extractors.cvalue_support.config import (
    BAD_ENDINGS_EN,
    HEURISTIC_MAX_LENGTH,
    SPACY_BOUNDARY_POS,
    SPACY_CANDIDATE_POS,
    STOP_WORDS,
)
from termlint.extraction.extractors.cvalue_support.types import TokenInfo


Candidate = Tuple[str, List[int]]


def group_by_sentence(token_info: List[TokenInfo]) -> Iterable[List[Tuple[int, TokenInfo]]]:
    """Yield tokens grouped by sentence while preserving original token indices."""
    grouped: Dict[int, List[Tuple[int, TokenInfo]]] = defaultdict(list)
    for idx, token in enumerate(token_info):
        grouped[token["sent_id"]].append((idx, token))

    for sent_id in sorted(grouped):
        yield grouped[sent_id]


class BaseCandidateGenerator(ABC):
    """Base interface for candidate generators."""

    def __init__(self, min_length: int, max_length: int):
        self.min_length = min_length
        self.max_length = max_length

    @abstractmethod
    def generate(self, tokens: List[str], token_info: List[TokenInfo]) -> List[Candidate]:
        """Generate candidate terms as `(text, token_indices)` tuples."""


class SpacyCandidateGenerator(BaseCandidateGenerator):
    """Generate noun-phrase-like candidates from spaCy token metadata.

    Rule:
        ADJ* + (NOUN|PROPN)+

    Boundaries:
        VERB, AUX, conjunctions, adpositions, determiners, pronouns,
        particles, punctuation, adverbs.
    """

    @staticmethod
    def _is_candidate_token(token: TokenInfo) -> bool:
        return (
            token["pos"] in SPACY_CANDIDATE_POS
            and not token["is_punct"]
            and len(token["token"]) > 2
        )

    @staticmethod
    def _is_boundary_token(token: TokenInfo) -> bool:
        return token["is_punct"] or token["pos"] in SPACY_BOUNDARY_POS

    @staticmethod
    def _is_np_like(window: List[TokenInfo]) -> bool:
        """Validate the pattern `ADJ* + (NOUN|PROPN)+`."""
        if not window:
            return False

        poses = [token["pos"] for token in window]
        if not all(pos in SPACY_CANDIDATE_POS for pos in poses):
            return False
        if poses[-1] not in {"NOUN", "PROPN"}:
            return False

        first_head = next((i for i, pos in enumerate(poses) if pos in {"NOUN", "PROPN"}), None)
        if first_head is None:
            return False

        return (
            all(pos == "ADJ" for pos in poses[:first_head])
            and all(pos in {"NOUN", "PROPN"} for pos in poses[first_head:])
        )

    def generate(self, tokens: List[str], token_info: List[TokenInfo]) -> List[Candidate]:
        """Generate spaCy-based candidates from sentence-local segments."""
        candidates: List[Candidate] = []

        for sentence in group_by_sentence(token_info):
            sent_indices = [idx for idx, _ in sentence]
            sent_tokens = [token for _, token in sentence]
            size = len(sent_tokens)

            i = 0
            while i < size:
                token = sent_tokens[i]
                if self._is_boundary_token(token) or not self._is_candidate_token(token):
                    i += 1
                    continue

                j = i
                segment_tokens: List[TokenInfo] = []
                segment_indices: List[int] = []

                while j < size:
                    current = sent_tokens[j]
                    if self._is_boundary_token(current) or not self._is_candidate_token(current):
                        break

                    segment_tokens.append(current)
                    segment_indices.append(sent_indices[j])
                    j += 1

                seg_len = len(segment_tokens)
                for start in range(seg_len):
                    min_end = start + self.min_length
                    max_end = min(seg_len, start + self.max_length)
                    for end in range(min_end, max_end + 1):
                        window = segment_tokens[start:end]
                        if self._is_np_like(window):
                            indices = segment_indices[start:end]
                            candidates.append((" ".join(tokens[k] for k in indices), indices))

                i = max(j, i + 1)

        return candidates


class HeuristicCandidateGenerator(BaseCandidateGenerator):
    """Generate fallback candidates with conservative language-agnostic heuristics.

    Rules:
        - work inside sentence boundaries only
        - use short n-grams only
        - reject candidates containing stop words
        - reject candidates with suspicious capitalization
        - reject candidates ending with common English verb-like forms
    """

    @staticmethod
    def _contains_stopword(indices: List[int], token_info: List[TokenInfo]) -> bool:
        return any(token_info[i]["lemma"] in STOP_WORDS for i in indices)

    @staticmethod
    def _is_title_case(word: str) -> bool:
        return len(word) > 1 and word[0].isupper() and word[1:].islower()

    def _has_bad_capitalization(self, indices: List[int], token_info: List[TokenInfo]) -> bool:
        words = [token_info[i]["token"] for i in indices]
        title_positions = [i for i, word in enumerate(words) if self._is_title_case(word)]
        non_initial_title = [i for i in title_positions if i != 0]
        return len(non_initial_title) > 1

    @staticmethod
    def _has_bad_ending(indices: List[int], token_info: List[TokenInfo]) -> bool:
        return token_info[indices[-1]]["lemma"] in BAD_ENDINGS_EN

    def _is_valid(self, indices: List[int], token_info: List[TokenInfo]) -> bool:
        words = [token_info[i]["token"] for i in indices]
        return not (
            self._contains_stopword(indices, token_info)
            or self._has_bad_capitalization(indices, token_info)
            or self._has_bad_ending(indices, token_info)
            or any(len(word) < 3 for word in words)
        )

    def generate(self, tokens: List[str], token_info: List[TokenInfo]) -> List[Candidate]:
        """Generate conservative fallback candidates with short n-grams."""
        candidates: List[Candidate] = []
        max_length = min(self.max_length, HEURISTIC_MAX_LENGTH)

        for sentence in group_by_sentence(token_info):
            sent_indices = [idx for idx, _ in sentence]
            sent_len = len(sent_indices)

            for length in range(self.min_length, max_length + 1):
                for start in range(sent_len - length + 1):
                    indices = sent_indices[start:start + length]
                    if self._is_valid(indices, token_info):
                        candidates.append((" ".join(tokens[k] for k in indices), indices))

        return candidates
