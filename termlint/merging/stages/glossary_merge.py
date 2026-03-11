from termlint.core.types import EntityStream, Result
from termlint.merging.converters.text_to_entity import TextToEntityConverter
from termlint.merging.stages.base import MergingStage


class GlossaryMergeStage(MergingStage):
    """
    Should take TextEntityStream and return new EntityStream
    """

    async def merge(self, converter: TextToEntityConverter) -> Result[EntityStream]:
        ...
