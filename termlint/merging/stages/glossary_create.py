from termlint.core.stages import ProcessingStage
from termlint.core.types import EntityStream, Result


class GlossaryCreateStage(ProcessingStage[EntityStream, EntityStream]):
    """
    This stage is intentionally thin if creation just means “these entities are now the glossary”.
    """
    async def process(self, stream: EntityStream) -> Result[EntityStream]:
        return Result.ok(stream)
