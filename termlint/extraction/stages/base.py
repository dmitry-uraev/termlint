"""Base class for extraction stages in the term extraction pipeline"""
from abc import ABC, abstractmethod
from typing import Optional

from termlint.core.types import Result, TextEntityStream


class ExtractionStage(ABC):
    """Base class for extraction stages in the term extraction pipeline"""

    def __init__(self, next_stage: Optional['ExtractionStage'] = None):
        self._next = next_stage

    async def process(self, stream: TextEntityStream) -> Result[TextEntityStream]:
        """Chain the processing of the next stage if it exists"""
        result = await self._handle(stream)
        if not result.is_ok:
            return result  # Propagate error without processing next stage
        return await self._next.process(result.value) if self._next else result

    @abstractmethod
    async def _handle(self, stream: TextEntityStream) -> Result[TextEntityStream]:
        """Handle processing of the current stage"""
