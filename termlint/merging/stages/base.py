"""
Base merging stage contract
"""


from abc import abstractmethod
from typing import AsyncIterator

from termlint.core.stages import ProcessingStage
from termlint.core.types import Result
from termlint.merging.converters.base import StreamConverter


class MergingStage(ProcessingStage):
    """
    Abstract base class for merge stages in the termlint pipeline.

    Concept:

    1. Merge TextEntityStream -> EntityStream
    """

    @abstractmethod
    async def merge(self, converter: StreamConverter) -> Result[AsyncIterator]:
        ...
