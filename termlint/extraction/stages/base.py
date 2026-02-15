"""Base class for extraction stages in the term extraction pipeline"""
from abc import ABC, abstractmethod

from termlint.core.types import Result, TextEntityStream
from termlint.core.stages import ProcessingStage


class ExtractionStage(ProcessingStage[TextEntityStream, TextEntityStream], ABC):
    """Base class for extraction stages in the term extraction pipeline"""

    async def process(self, stream: TextEntityStream) -> Result[TextEntityStream]:
        """Chain the processing of the next stage if it exists"""
        return await self._handle(stream)

    @abstractmethod
    async def _handle(self, stream: TextEntityStream) -> Result[TextEntityStream]:
        """Handle processing of the current stage"""
