from termlint.core.stages import ProcessingStage
from termlint.core.types import EntityStream, Result, TextEntityStream
from termlint.entity_building.protocols import TextEntityBuilder, TextEntitySelector


class TextToEntityStage(ProcessingStage[TextEntityStream, EntityStream]):

    def __init__(
        self,
        builder: TextEntityBuilder,
        selector: TextEntitySelector | None = None
    ) -> None:
        self.builder= builder
        self.selector = selector

    async def process(self, stream: TextEntityStream) -> Result[EntityStream]:
        if self.selector is not None:
            selected = await self.selector.select(stream)
            if not selected.ok:
                return Result.err(selected.errors)
            stream = selected.value

        return await self.builder.build(stream)
