"""C-Value scoring for pre-generated term candidates."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Tuple

Candidate = Tuple[str, List[int]]
CValueResult = Tuple[str, float, int, List[int]]


class CValueScorer:
    """Score pre-generated term candidates with the C-Value formula.

    The scorer expects candidates as `(text, token_indices)` tuples, where:
        - `text` is the normalized candidate string
        - `token_indices` are positions of the candidate tokens in the source text

    Scoring:
        - non-nested candidate:
            log2(length) * frequency
        - nested candidate:
            log2(length) * (frequency - average_parent_frequency)

    Notes:
        - Single-token candidates receive score `0.0` because `log2(1) = 0`
        - The first occurrence is preserved in the result for span reconstruction
    """

    def __init__(self, min_freq: int = 1):
        self.min_freq = min_freq

    def compute(self, candidates: List[Candidate]) -> List[CValueResult]:
        """Compute C-Value scores for candidates.

        Args:
            candidates: Candidate terms as `(text, token_indices)` tuples.

        Returns:
            A list of `(text, score, frequency, first_indices)` tuples.
        """
        if not candidates:
            return []

        aggregated = self._aggregate(candidates)
        nested_in = self._build_nested_index(aggregated)

        results: List[CValueResult] = []
        for text, data in aggregated.items():
            freq = data["freq"]
            length = data["length"]
            parent_freqs = nested_in.get(text, [])

            if length <= 1:
                score = 0.0
            elif parent_freqs:
                score = math.log2(length) * (freq - sum(parent_freqs) / len(parent_freqs))
            else:
                score = math.log2(length) * freq

            results.append((text, max(0.0, score), freq, data["occurrences"][0]))

        return results

    def _aggregate(self, candidates: List[Candidate]) -> Dict[str, Dict]:
        """Aggregate repeated candidates by text."""
        aggregated: Dict[str, Dict] = {}

        for text, indices in candidates:
            if text not in aggregated:
                aggregated[text] = {
                    "freq": 0,
                    "occurrences": [],
                    "length": len(indices),
                }

            aggregated[text]["freq"] += 1
            aggregated[text]["occurrences"].append(indices)

        return {
            text: data
            for text, data in aggregated.items()
            if data["freq"] >= self.min_freq
        }

    def _build_nested_index(self, candidates: Dict[str, Dict]) -> Dict[str, List[int]]:
        """Map each candidate to frequencies of longer parent candidates."""
        nested_in: Dict[str, List[int]] = defaultdict(list)
        candidate_texts = list(candidates.keys())

        for term in candidate_texts:
            term_words = term.split()
            term_len = len(term_words)

            for parent in candidate_texts:
                parent_words = parent.split()
                parent_len = len(parent_words)

                if parent_len <= term_len:
                    continue

                for start in range(parent_len - term_len + 1):
                    if parent_words[start:start + term_len] == term_words:
                        nested_in[term].append(candidates[parent]["freq"])
                        break

        return nested_in
