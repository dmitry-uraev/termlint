from termlint.core.stages import ProcessingStage
from termlint.core.types import EntityStream, MatchResultStream, Result

from termlint.entity_building.protocols import MatchResultEntityBuilder, MatchResultEntitySelector


class MatchResultsToEntityStage(ProcessingStage[MatchResultStream, EntityStream]):
    def __init__(
        self,
        builder: MatchResultEntityBuilder,
        selector: MatchResultEntitySelector | None = None
    ) -> None:
        self.builder = builder
        self.selector = selector

    async def process(self, stream: MatchResultStream) -> Result[EntityStream]:
        if self.selector is not None:
            selected = await self.selector.select(stream)
            if not selected.ok:
                return Result.err(selected.errors)
            stream = selected.value

        return await self.builder.build(stream)
