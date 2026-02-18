"""Unified pipeline for termlint stages"""
import asyncio
from typing import List
from termlint.core.models import MatchResult, TextEntity
from termlint.core.stages import ProcessingStage
from termlint.core.types import MatchResultStream, Result, TextEntityStream
from termlint.extraction.stages import NormalizationStage
from termlint.extraction.extractors import RuleExtractor, BaseExtractor
from termlint.extraction.stages.parallel import ParallelStage
from termlint.verifier import ExactVerificationStage, KnowledgeSource, FuzzyVerificationStage
from termlint.utils import get_child_logger, timeit

logger= get_child_logger('UnifiedPipeline')


StageResultStream = Result[MatchResultStream] | Result[TextEntityStream]
PipelineResult = Result[List[MatchResult]] | Result[List[TextEntity]]


class UnifiedPipeline:
    """Fluent API to create term processing pipelines"""

    def __init__(self):
        self._extractors: List[BaseExtractor] = []
        self._stages: List[ProcessingStage] = []

    # ==================== Extractors =================================

    def extractors(self, *extractors: BaseExtractor) -> 'UnifiedPipeline':
        """Parallel extractors: str -> TextEntityStream"""
        self._extractors.extend(extractors)
        return self

    def with_rules(self, model: str = 'en_core_web_sm') -> 'UnifiedPipeline':
        """Rule-based extraction"""
        self._extractors.append(RuleExtractor(model=model))
        return self

    # ==================== Stages =====================================

    def normalize(self) -> 'UnifiedPipeline':
        """Adds NormalizationStage (TextEntityStream → TextEntityStream)"""
        self._stages.append(NormalizationStage())
        return self

    # def filter(self, min_score: float = 0.2, min_length: int = 2) -> 'UnifiedPipeline[TextEntityStream, TextEntityStream]':
    #     """TODO: Adds filter stage"""
    #     logger.warning("Filter stage not implemented yet")
    #     return self

    def verify(self, verifier: ProcessingStage | KnowledgeSource) -> 'UnifiedPipeline':
        """Adds VerificationStage"""
        if isinstance(verifier, KnowledgeSource):
            stage = ExactVerificationStage(verifier)
        else:
            stage = verifier
        self._stages.append(stage)
        return self

    def stage(self, stage: ProcessingStage) -> 'UnifiedPipeline':
        """Adds custom stage"""
        self._stages.append(stage)
        return self

    # ==================== Execute ====================================

    @timeit
    async def run(self, text: str) -> StageResultStream:
        """Execute pipeline (str -> TextEntityStream | MatchResultStream)"""
        logger.info(f"Running pipeline with {len(self._extractors)} extractors + {len(self._stages)} stages")

        if not self._extractors:
            return Result.err(["No extractors defined"])

        extract_result = await ParallelStage(self._extractors).extract(text)
        if not extract_result.is_ok:
            return extract_result

        stream = extract_result.value
        for i, stage in enumerate(self._stages):
            logger.debug(f"Stage {i+1}/{len(self._stages)}: {stage.__class__.__name__}")

            stage_result = await stage.process(stream)
            if not stage_result.is_ok:
                logger.error(f"Stage failed: {stage_result.errors}")

            stream = stage_result.value

        return Result.ok(stream)

    @timeit
    async def run_unified(self, text: str) -> PipelineResult:
        """TODO: Execute pipeline (single call for extractors + stages)"""
        logger.info(f"Running pipeline with {len(self._stages)} stages")

        current_data = text

        for i, stage in enumerate(self._stages):
            logger.debug(f"Stage {i+1}/{len(self._stages)}: {stage.__class__.__name__}")

            stage_result = await stage.process(current_data)
            if not stage_result.is_ok:
                logger.error(f"Stage {stage.__class__.__name__} failed: {stage_result.errors}")
                return stage_result

            current_data = stage_result.value

        logger.info("Pipeline completed successfully")
        return Result.ok(current_data)

    async def run_and_collect(self, text: str) -> PipelineResult:
        """Convenience: gather results into list"""
        result = await self.run(text)
        if not result.is_ok:
            return Result.err(result.errors)

        collect_result = await result.value.to_list()
        if not collect_result.is_ok:
            return Result.err(collect_result.errors)

        return Result.ok(collect_result.value)


def pipeline() -> UnifiedPipeline:
    """Factory function"""
    return UnifiedPipeline()


async def demo():
    from termlint.constants import TESTS_DIR
    from termlint.verifier import JSONGlossarySource
    from pprint import pprint

    source = JSONGlossarySource(TESTS_DIR / 'fixtures' / 'test_glossary.json')
    await source.initialize()

    text = """
    Нейронные сети машинного обучения обрабатывают большие данные.
    Искусственный интеллект использует глубокое обучение.
    """

    fuzzy_stage = FuzzyVerificationStage(source)#, threshold=60, limit=3, use_lemma=False)

    result = await (pipeline()
        .extractors(RuleExtractor(model='ru_core_news_sm'))
        # .normalize()
        .verify(fuzzy_stage)
        .run_and_collect(text))

    if result.is_ok:
        stream = result.value
        for entity in stream:
            pprint(entity)
        return
    else:
        pprint(f"Pipeline failed: {result.errors}")


if __name__ == "__main__":
    asyncio.run(demo())
