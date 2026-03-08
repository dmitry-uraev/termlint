"""C-Value based term extractor.

The extractor ranks multi-word term candidates with the C-Value formula:

    CValue(a) = log2(|a|) * f(a)                              if a is not nested
    CValue(a) = log2(|a|) * (f(a) - avg_parent_frequency(a))  otherwise

Where:
    - |a| is the candidate length in tokens
    - f(a) is the candidate frequency
    - parent terms are longer candidates that contain `a` as a contiguous span

Candidate generation is delegated to one of two strategies:

    1. spaCy mode (default when available):
       noun-phrase-like candidates built from POS tags

    2. heuristic mode:
       short conservative n-grams used as a fallback
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import AsyncIterator, Dict, List, Tuple

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

from termlint.core.models import TextEntity
from termlint.extraction.extractors.base import BaseExtractor
from termlint.utils.logger import get_child_logger

from termlint.extraction.extractors.cvalue_support.scorer import CValueScorer, CValueResult

from termlint.extraction.extractors.cvalue_support.candidate_generators import (
    BaseCandidateGenerator,
    HeuristicCandidateGenerator,
    SpacyCandidateGenerator,
)
from termlint.extraction.extractors.cvalue_support.config import (
    DEFAULT_MAX_LENGTH,
    DEFAULT_MIN_FREQ,
    DEFAULT_MIN_LENGTH,
    DEFAULT_MODEL,
    DEFAULT_THRESHOLD,
)
from termlint.extraction.extractors.cvalue_support.tokenizer import tokenize_with_regex, tokenize_with_spacy
from termlint.extraction.extractors.cvalue_support.types import TokenInfo

logger = get_child_logger("CValueExtractor")

CValueResult = Tuple[str, float, int, List[int]]


class CValueExtractor(BaseExtractor):
    """Extract term candidates and rank them with C-Value.

    Args:
        threshold: Minimum accepted C-Value score.
        min_freq: Minimum candidate frequency.
        min_length: Minimum candidate length in tokens.
        max_length: Maximum candidate length in tokens.
        use_ling_filter: Enable spaCy-based candidate generation.
        model: spaCy model name to load when linguistic filtering is enabled.
        auto_download: Download the spaCy model if it is missing.

    Notes:
        spaCy mode is preferred because it uses POS-aware candidate generation.
        When spaCy is unavailable or the model cannot be loaded, the extractor
        falls back to heuristic candidate generation.
    """

    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        min_freq: int = DEFAULT_MIN_FREQ,
        min_length: int = DEFAULT_MIN_LENGTH,
        max_length: int = DEFAULT_MAX_LENGTH,
        use_ling_filter: bool = True,
        model: str = DEFAULT_MODEL,
        auto_download: bool = False,
    ):
        super().__init__()
        self.threshold = threshold
        self.min_freq = min_freq
        self.min_length = min_length
        self.max_length = max_length
        self.model = model
        self.auto_download = auto_download

        self.scorer = CValueScorer(min_freq=min_freq)

        self.nlp = self._load_model(model) if use_ling_filter and SPACY_AVAILABLE else None
        self.use_ling_filter = self.nlp is not None

        self.generator: BaseCandidateGenerator
        if self.use_ling_filter:
            self.generator = SpacyCandidateGenerator(min_length=min_length, max_length=max_length)
        else:
            self.generator = HeuristicCandidateGenerator(min_length=min_length, max_length=max_length)

    def _load_model(self, model: str):
        """Load a spaCy model and optionally download it if missing."""
        try:
            return spacy.load(model)
        except OSError:
            if not self.auto_download:
                logger.warning(
                    "spaCy model '%s' is unavailable. Falling back to heuristic mode.",
                    model,
                )
                return None

            from spacy.cli.download import download as spacy_download

            spacy_download(model)
            return spacy.load(model)

    def _tokenize(self, text: str) -> List[TokenInfo]:
        """Tokenize text with spaCy when available, otherwise use regex fallback."""
        if self.use_ling_filter and self.nlp is not None:
            return tokenize_with_spacy(self.nlp, text)
        return tokenize_with_regex(text)

    async def _extract(self, text: str) -> AsyncIterator[TextEntity]:
        """Extract ranked terms from input text."""
        if not text.strip():
            return

        token_info = self._tokenize(text)
        if len(token_info) < self.min_length:
            return

        tokens = [token["token"] for token in token_info]
        results = self._score_candidates(tokens=tokens, token_info=token_info)

        seen = set()
        for term_text, score, freq, indices in sorted(
            results,
            key=lambda item: (-item[1], -len(item[3]), -item[2], item[0].lower()),
        ):
            if freq < self.min_freq or score < self.threshold or term_text in seen:
                continue

            seen.add(term_text)
            yield TextEntity(
                text=term_text,
                original_text=term_text,
                lemma=term_text.lower(),
                span=(
                    token_info[indices[0]]["char_start"],
                    token_info[indices[-1]]["char_end"],
                ),
                score=score,
                frequency=freq,
                extractor_type="cvalue",
                properties={"length": len(indices)},
            )

    def _score_candidates(self, tokens: List[str], token_info: List[TokenInfo]) -> List[CValueResult]:
        candidates = self.generator.generate(tokens=tokens, token_info=token_info)
        return self.scorer.compute(candidates)


async def run_demo(
    mode: str,
    text: str,
    threshold: float = 0.0,
    min_freq: int = 1,
    min_length: int = 2,
    max_length: int = 4,
    model: str = DEFAULT_MODEL,
) -> None:
    mode = mode.lower().strip()

    if mode not in {"heuristic", "spacy"}:
        raise ValueError("mode must be either 'heuristic' or 'spacy'")

    use_ling_filter = mode == "spacy"

    extractor = CValueExtractor(
        threshold=threshold,
        min_freq=min_freq,
        min_length=min_length,
        max_length=max_length,
        use_ling_filter=use_ling_filter,
        model=model,
        auto_download=False,
    )

    print(f"\n{'=' * 60}")
    print(f"🎯 C-VALUE MODE: {mode.upper()}")
    print(f"model={extractor.model}, use_ling_filter={extractor.use_ling_filter}")
    print(f"{'=' * 60}")

    found = False
    async for e in extractor._extract(text):
        found = True
        print(f"  {e.text}: {e.score:.2f} (x{e.frequency})")

    if not found:
        print("  Ничего не найдено.")

    if mode == "spacy" and not extractor.use_ling_filter:
        print("\n⚠️ spaCy-режим не активировался.")
        print(f"Проверь установку модели: {model}")


async def demo() -> None:
    ru_text = """
    Нейронные сети и методы машинного обучения обрабатывают большие данные.
    Искусственный интеллект использует глубокое обучение.
    """

    en_text = """
    Neural networks and machine learning methods process large datasets.
    Artificial intelligence uses deep learning.
    """

    print("\n########## RUSSIAN ##########")
    await run_demo("heuristic", ru_text, model="ru_core_news_sm")
    await run_demo("spacy", ru_text, model="ru_core_news_sm")

    print("\n########## ENGLISH ##########")
    await run_demo("heuristic", en_text, model="en_core_web_sm")
    await run_demo("spacy", en_text, model="en_core_web_sm")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
