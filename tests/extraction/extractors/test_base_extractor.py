import pytest
from typing import AsyncIterator, List

from termlint.core.models import TextEntity
from termlint.extraction.extractors.base import BaseExtractor, ConfigurableExtractor


class DummyExtractor(BaseExtractor):
    """A dummy extractor that yields each word as a TextEntity."""

    def __init__(self) -> None:
        self.calls: List[str] = []

    async def _extract(self, text: str) -> AsyncIterator[TextEntity]:
        self.calls.append(text)
        yield TextEntity(
            text=text,
            original_text=text,
            lemma=text.lower().replace(" ", "_"),
            span=(0, len(text.split())),
            score=1.0,
        )
