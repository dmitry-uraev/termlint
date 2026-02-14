from typing import AsyncIterator, List

from termlint.core.models import TextEntity
from termlint.extraction.extractors.base import ConfigurableExtractor


class DummyConfigurableExtractor(ConfigurableExtractor):
    """A dummy extractor that yields each word as a TextEntity."""
    async def _extract(self, text: str) -> AsyncIterator[TextEntity]:
        yield TextEntity(
            text=text,
            original_text=text,
            lemma=text.lower().replace(" ", "_"),
            span=(0, len(text.split())),
            score=1.0,
        )


async def test_configurable_extractor_stores_config():
    """Test that ConfigurableExtractor stores the configuration correctly."""
    extractor = DummyConfigurableExtractor(foo=1, bar="x")
    assert extractor.config == {"foo": 1, "bar": "x"}

    entities: List[TextEntity] = []
    async for entity in extractor("test"):
        entities.append(entity)

    assert len(entities) == 1
    assert entities[0].text == "test"
