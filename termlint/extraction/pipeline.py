"""
Text extraction pipeline implementation
"""

import asyncio
from typing import List

from termlint.core.models import TextEntity
from termlint.core.types import Result, TextEntityStream
from termlint.extraction.stages.base import ExtractionStage
from termlint.extraction.stages.normalize import NormalizationStage
from termlint.extraction.stages.parallel import ParallelStage
from termlint.extraction.extractors.base import BaseExtractor
from termlint.extraction.extractors.rule import RuleExtractor


class TextExtractionPipeline:
    """
    Fluent API for text extraction pipeline
    """

    def __init__(self):
        self._extractors: List[BaseExtractor] = []
        self._stages: List[ExtractionStage] = []

    # ==================== EXTRACTORS ====================
    def extractors(self, *extractors: BaseExtractor) -> 'TextExtractionPipeline':
        """Add parallel text extractors"""
        self._extractors.extend(extractors)
        return self

    def with_rules(self) -> 'TextExtractionPipeline':
        """Add rule-based extractor (TODO)"""
        self._extractors.append(RuleExtractor())
        return self

    def with_cvalue(self) -> 'TextExtractionPipeline':
        """Add C-Value extractor (TODO)"""
        # from .extractors.cvalue import cvalue_extractor
        # self._extractors.append(cvalue_extractor)
        return self

    # ==================== STAGES ====================
    def normalize(self) -> 'TextExtractionPipeline':
        """Add normalization stage"""
        self._stages.append(NormalizationStage())
        return self

    def filter(self, min_score: float = 0.2, min_length: int = 2) -> 'TextExtractionPipeline':
        """Add filtering stage"""
        # from .stages.filter import FilterStage
        # self._stages.append(FilterStage(min_score=min_score, min_length=min_length))
        return self

    def rank(self) -> 'TextExtractionPipeline':
        """Add ranking stage (TODO)"""
        # from .stages.rank import RankStage
        # self._stages.append(RankStage())
        return self

    # ==================== EXECUTE ====================
    async def run(self, text: str) -> Result[TextEntityStream]:
        """Execute full pipeline: Text → Parallel Extractors → Stages → TextEntityStream"""
        if not self._extractors:
            return Result.err(["No extractors defined in the pipeline"])

        # 1. Parallel extraction
        extract_result = await ParallelStage(self._extractors).extract(text)
        if not extract_result.is_ok:
            return extract_result  # Propagate extractor errors

        # 2. Sequential processing
        stream = extract_result.value
        for stage in self._stages:
            stage_result = await stage.process(stream)
            if not stage_result.is_ok:
                return stage_result  # Propagate stage errors
            stream = stage_result.value

        return Result.ok(stream)

    async def run_and_collect(self, text: str) -> Result[List[TextEntity]]:
        """Convenience: run pipeline and collect results to list"""
        pipeline_result = await self.run(text)
        if not pipeline_result.is_ok:
            return Result.err(pipeline_result.errors)

        collect_result = await pipeline_result.value.to_list()
        if not collect_result.is_ok:
            return Result.err(collect_result.errors)
        return Result.ok(collect_result.value)

    def to_list(self, text: str) -> Result[asyncio.Future[List[TextEntity]]]:
        """Convenience: run pipeline and collect to list"""
        async def collect():
            result = await self.run(text)
            if not result.is_ok:
                return Result.err(result.errors)
            return await result.value.to_list()
        return Result.ok(asyncio.ensure_future(collect()))

# ==================== FACTORY ====================
def pipeline() -> TextExtractionPipeline:
    """Factory function for fluent API"""
    return TextExtractionPipeline()


async def example_main():
    """Example usage of the text extraction pipeline"""
    text = """
    Нейронные сети машинного обучения обрабатывают большие данные.
    Искусственный интеллект использует глубокое обучение.
    """

    result = await (pipeline()
                    .extractors(RuleExtractor(model="ru_core_news_sm"))
                    .normalize()
                    .filter(min_score=0.5)
                    .run_and_collect(text))

    result.map(lambda entities: print(f"Extracted entities: {entities}")) \
          .map(lambda _: print("Pipeline executed successfully"))

if __name__ == "__main__":
    asyncio.run(example_main())
