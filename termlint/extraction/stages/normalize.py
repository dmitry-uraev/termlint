"""
Normalization stage for text entity extraction pipeline.
"""
import asyncio

from termlint.core.models import TextEntity
from termlint.core.types import Result, TextEntityStream
from termlint.extraction.stages.base import ExtractionStage


class NormalizationStage(ExtractionStage):
    """
    Normalization stage for text entity extraction pipeline
    """
    async def _handle(self, stream: TextEntityStream) -> Result[TextEntityStream]:
        async def normalize():
            async for entity in stream:
                yield TextEntity(
                    text=entity.text.lower().strip(),
                    original_text=entity.original_text,
                    lemma=entity.text.lower(),
                    span=entity.span,
                    score=entity.score,
                    pos_tags=entity.pos_tags,
                    sentence=entity.sentence,
                    frequency=entity.frequency,
                    extractor_type=f"{entity.extractor_type}_normalized",
                    properties=entity.properties
                )
        return Result.ok(TextEntityStream(normalize()))


async def example_main():
    """Example usage of NormalizationStage"""
    # TODO example to tests


if __name__ == "__main__":
    asyncio.run(example_main())
