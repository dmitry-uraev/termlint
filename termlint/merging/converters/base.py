"""
Base protocol for all converters
"""

from typing import AsyncIterator, Protocol


class StreamConverter(Protocol):

    async def convert(self, input_stream: AsyncIterator) -> AsyncIterator:
        ...
