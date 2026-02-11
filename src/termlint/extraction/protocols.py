from typing import Protocol, AsyncIterator
from src.termlint.core.models import TextEntity
from src.termlint.core.types import TextEntityStream


class SingleEntityProcessor(Protocol):
    """Protocol for processing a single TextEntity (for parallel processing stage)."""
    async def process_single(self, entity: TextEntity) -> TextEntity:
        ...


class StreamProcessor(Protocol):
    """Protocol for processing a stream of TextEntities (for sequential processing stage)."""
    async def process(self, stream: TextEntityStream) -> TextEntityStream:
        ...
