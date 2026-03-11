

from typing import Protocol

from termlint.core.types import Result, EntityStream, MatchResultStream, TextEntityStream


class TextEntitySelector(Protocol):
    async def select(self, stream: TextEntityStream) -> Result[TextEntityStream]:
        ...


class MatchResultEntitySelector(Protocol):
    async def select(self, stream: MatchResultStream) -> Result[MatchResultStream]:
        ...


class TextEntityBuilder(Protocol):
    async def build(self, stream: TextEntityStream) -> Result[EntityStream]:
        ...


class MatchResultEntityBuilder(Protocol):
    async def build(self, stream: MatchResultStream) -> Result[EntityStream]:
        ...
