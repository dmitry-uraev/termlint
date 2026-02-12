"""
Tests for TextEntityStream type
"""

from typing import AsyncIterator

from termlint.core.models import TextEntity
from termlint.core.types import TextEntityStream


async def test_text_entity_stream_ideal(sample_text_entity):
    """Test TextEntityStream with ideal input"""
    stream = TextEntityStream.from_list([sample_text_entity])
    entities = (await stream.to_list()).value
    assert len(entities) == 1

async def test_text_entity_stream_from_generator(sample_text_entity):
    """Test TextEntityStream created from an async generator"""
    async def generator() -> AsyncIterator[TextEntity]:
        yield sample_text_entity

    stream = TextEntityStream.from_generator(generator)
    entities = (await stream.to_list()).value
    assert len(entities) == 1
