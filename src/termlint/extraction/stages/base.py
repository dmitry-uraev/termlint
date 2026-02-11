from abc import ABC, abstractmethod
from typing import Optional

from src.termlint.core.types import TextEntityStream


class ExtractionStage(ABC):
    """Base class for extraction stages in the term extraction pipeline"""

    def __init__(self, next_stage: Optional['ExtractionStage'] = None):
        self._next = next_stage

    async def process(self, stream: TextEntityStream) -> TextEntityStream:
        """Chain the processing of the next stage if it exists"""
        transformed_stream = await self._handle(stream)
        return await self._next.process(transformed_stream) if self._next else transformed_stream

    @abstractmethod
    async def _handle(self, stream: TextEntityStream) -> TextEntityStream:
        """Handle processing of the current stage"""
        ...
