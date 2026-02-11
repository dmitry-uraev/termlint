from src.termlint.core.models import TextEntity
from src.termlint.core.types import TextEntityStream
from src.termlint.extraction.stages.base import ExtractionStage


class NormalizationStage(ExtractionStage):
    async def _handle(self, stream: TextEntityStream) -> TextEntityStream:
        async def normalize():
            async for entity in stream:
                yield TextEntity(
                    text=entity.text.lower(),
                    original_text=entity.original_text,
                    lemma=entity.text.lower(),
                    score=entity.score,
                    span=entity.span
                )
        return TextEntityStream(normalize())
