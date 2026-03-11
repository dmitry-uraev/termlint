from termlint.core.models import Entity
from termlint.core.stages import ProcessingStage
from termlint.core.types import EntityStream, Result
from termlint.glossary.models import MergePolicy, MergeResult


class GlossaryMergeStage(ProcessingStage[EntityStream, MergeResult]):

    def __init__(
        self,
        base_entities: list[Entity],
        policy: MergePolicy,
    ) -> None:
        self.base_entities = base_entities
        self.policy = policy

    async def process(self, stream: EntityStream) -> Result[MergeResult]:
        ...
