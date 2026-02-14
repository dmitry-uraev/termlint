from typing import AsyncIterator, List

import pytest

from termlint.core.models import TextEntity
from termlint.extraction.extractors.base import BaseExtractor


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


async def test_base_extractor_contract_single_iteration():
    """Test that BaseExtractor can be used in an async for loop and yields TextEntity objects."""
    extractor = DummyExtractor()
    text = "Natural language"

    entities: List[TextEntity] = []
    async for entity in extractor(text):
        entities.append(entity)

    assert len(entities) == 1
    e = entities[0]

    assert e.text == text
    assert e.original_text == text
    assert e.lemma == "natural_language"
    assert e.span == (0, 2)
    assert e.score == 1.0

    assert extractor.calls == [text]


async def test_base_extractor_raises_without_call():
    """Test that BaseExtractor cannot be used without calling it first."""
    extractor = DummyExtractor()
    with pytest.raises(ValueError):
        async for _ in extractor:
            pass
