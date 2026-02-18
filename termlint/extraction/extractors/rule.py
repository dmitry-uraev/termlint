"""
Rule-based text extraction using spaCy.
"""

try:
    import spacy
    from spacy.matcher.matcher import Matcher
    SPAcy_AVAILABLE = True
except ImportError:
    SPAcy_AVAILABLE = False


import subprocess
import sys
from typing import AsyncIterator, Dict, List, Optional

from termlint.core.models import TextEntity
from termlint.extraction.extractors.base import ConfigurableExtractor
from termlint.utils.logger import get_child_logger

logger = get_child_logger("RuleExtractor (spaCy)")


DEFAULT_MODEL = "en_core_web_sm"

DEFAULT_PATTERNS: List[List[Dict]] = [
    [{"POS": "NOUN"}, {"POS": "NOUN"}],  # noun compounds
    [{"POS": "ADJ"}, {"POS": "NOUN"}],   # adjective + noun
    [{"POS": "NOUN"}, {"POS": "ADJ"}],   # noun + adjective
    [{"POS": "NOUN"}, {"POS": "VERB"}, {"POS": "NOUN"}],  # noun + verb + noun
    [{"POS": "NOUN"}, {"IS_PUNCT": True}, {"POS": "NOUN"}],  # noun + punctuation + noun
]


class RuleExtractor(ConfigurableExtractor):
    """
    Rule-based extractor using spaCy's Matcher.

    Configuration:
    - patterns: List of spaCy matcher patterns
    - model: spaCy language model to use (default: 'en_core_web_sm')
    """

    def __init__(
        self,
        patterns: Optional[List[List[Dict]]] = DEFAULT_PATTERNS,
        model: Optional[str] = DEFAULT_MODEL,
        **kwargs
    ):
        if not SPAcy_AVAILABLE:
            raise ImportError("spaCy is required for RuleExtractor. Install: pip install termlint[rule].")
        super().__init__(patterns=patterns, model=model, **kwargs)

        self.model_name = self.config.get("model", DEFAULT_MODEL)
        try:
            self.nlp = spacy.load(self.model_name)
        except OSError:
            logger.warning(f"spaCy model '{self.model_name}' not found. Attempting to download...")
            self._download_model(self.model_name)
            self.nlp = spacy.load(self.model_name)
            logger.info(f"spaCy model '{self.model_name}' loaded successfully after download.")

        self.matcher = self._setup_matcher()

    def _download_model(self, model_name: str):
        """Download spaCy model if not already installed."""
        try:
            from spacy.cli.download import download as spacy_download
            spacy_download(model_name)
        except ImportError as e:
            subprocess.check_call([
                sys.executable, "-m", "spacy", "download", model_name
            ])

    def _setup_matcher(self) -> Matcher:
        matcher = Matcher(self.nlp.vocab)
        patterns = self.config.get("patterns", DEFAULT_PATTERNS)
        matcher.add("TERM_RULES", patterns)
        return matcher

    async def _extract(self, text: str) -> AsyncIterator[TextEntity]:
        """Extract terms using spaCy rule-based patterns."""
        doc = self.nlp(text)
        matches = self.matcher(doc)

        logger.info(f"Found {len(matches)} term candidates in '{text[:50]}...'")

        seen_spans = set()
        for match_id, start, end in matches:
            span_key = (start, end)
            if span_key in seen_spans:
                continue  # Skip duplicate spans
            seen_spans.add(span_key)

            span = doc[start:end]
            entity = TextEntity(
                text=span.text,
                original_text=span.text,
                lemma=" ".join(token.lemma_ for token in span),
                span=(start, end),
                score=self.config.get("min_score", 0.5),  # Default score for rule-based matches
                pos_tags=[token.pos_ for token in span],
                sentence=span.sent.text.strip() if span.sent else text[:100] + "...",
                frequency=1,
                extractor_type="rule",
                properties={
                    "pattern_id": match_id,
                    "token_count": len(span),
                }
            )
            logger.debug(f"  Extracted: '{entity.text}' → lemma='{entity.lemma}'")
            yield entity


async def example_main():
    """Example usage of RuleExtractor"""
    text = "Natural language processing enables computers to understand human language."

    extractor = RuleExtractor()
    async for entity in extractor(text):
        print(entity)

    extractor = RuleExtractor(
        patterns=[[{"POS": "NOUN", "OP": "+"}]],  # 2+ nouns
        model="en_core_web_sm",
        min_score=0.5
    )
    async for entity in extractor(text):
        print(entity)


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_main())
