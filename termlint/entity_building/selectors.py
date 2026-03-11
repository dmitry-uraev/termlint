
from termlint.core.models import MatchStatus
from termlint.core.types import MatchResultStream, Result, TextEntityStream


class PassThroughTextSelector:
    async def select(self, stream: TextEntityStream) -> Result[TextEntityStream]:
        return Result.ok(stream)


class UnknownMatchSelector:
    async def select(self, stream: MatchResultStream) -> Result[MatchResultStream]:
        async def _source():
            async for item in stream:
                if item.status == MatchStatus.UNKNOWN:
                    yield item

        return Result.ok(MatchResultStream(_source()))
