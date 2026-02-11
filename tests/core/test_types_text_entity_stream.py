from typing import AsyncIterator
from src.termlint.core.models import TextEntity
from src.termlint.core.types import TextEntityStream


async def test_text_entity_stream_ideal(sample_text_entity):
    stream = TextEntityStream.from_list([sample_text_entity])
    entities = await stream.to_list()
    assert len(entities) == 1

async def test_text_entity_stream_from_generator(sample_text_entity):

    async def generator() -> AsyncIterator[TextEntity]:
        yield sample_text_entity

    stream = TextEntityStream.from_generator(generator)
    entities = await stream.to_list()
    assert len(entities) == 1
