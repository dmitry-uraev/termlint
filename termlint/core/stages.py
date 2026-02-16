from abc import ABC, abstractmethod
from typing import Generic, TypeVar, AsyncIterator

from termlint.core.types import Result

TInput = TypeVar('TInput')
TOutput = TypeVar('TOutput')


class ProcessingStage(ABC, Generic[TInput, TOutput]):
    """Abstract base class for processing stages in the termlint pipeline."""
    @abstractmethod
    async def process(self, input_data: TInput) -> Result[TOutput]:
        """Process input -> output asynchronously with streaming results."""
        ...
