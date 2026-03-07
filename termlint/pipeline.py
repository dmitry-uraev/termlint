"""Unified pipeline for termlint stages"""
import asyncio

from typing import Callable, List, Optional

from termlint.config import TermlintConfig, VerifierConfig
from termlint.core.models import MatchResult, QualityConfig, Report, ReportConfig, ReportType, TextEntity
from termlint.core.stages import ProcessingStage
from termlint.core.types import MatchResultStream, Result, TextEntityStream

from termlint.extraction import NormalizationStage, ParallelStage, BaseExtractor
from termlint.verifier import FuzzyVerificationStage, VerifierFactory
from termlint.reporter import ReportStage

from termlint.utils import get_child_logger, timeit

logger= get_child_logger('UnifiedPipeline')


StageResultStream = Result[MatchResultStream] | Result[TextEntityStream]
PipelineResult = Result[List[MatchResult]] | Result[List[TextEntity]] | Result[List[Report]]
ProgressCallback = Callable[[int, int, str], None]


class UnifiedPipeline:
    """Fluent API to create term processing pipelines"""

    def __init__(self):
        self._extractors: List[BaseExtractor] = []
        self._stages: List[ProcessingStage] = []

    # ==================== Config Bridge ==============================

    @classmethod
    async def from_config(cls, config: TermlintConfig) -> 'UnifiedPipeline':
        """Created pipeline from TermlintConfig (pyproject.toml)"""
        pipeline = cls()

        for stage_name in config.pipeline.stages:
            match stage_name:
                case "extract":
                    for name in config.extraction.extractors:
                        if name == "rule":
                            model = config.extraction.rules.get("model", "ru_core_news_sm")
                            auto_download_model = bool(config.extraction.rules.get("auto_download_model", False))
                            pipeline.with_rules(model=model, auto_download_model=auto_download_model)
                case "normalize":
                    pipeline.normalize()
                case "verify":
                    verifier = await VerifierFactory.create(config.verifier)
                    pipeline.verify(verifier)

                case "report":
                    report_config = ReportConfig(
                        include=[getattr(ReportType, t.upper()) for t in config.reports.include],
                        exporters=config.reports.exporters
                    )
                    quality_config = config.quality_gates.to_quality_config()
                    pipeline.report(report_config, quality_config)

        logger.info(f"Pipeline created from config")
        return pipeline

    # ==================== Extractors =================================

    def extractors(self, *extractors: BaseExtractor) -> 'UnifiedPipeline':
        """Parallel extractors: str -> TextEntityStream"""
        self._extractors.extend(extractors)
        return self

    def with_rules(
        self,
        model: str = 'en_core_web_sm',
        auto_download_model: bool = False
    ) -> 'UnifiedPipeline':
        """Rule-based extraction"""
        from termlint.extraction.extractors.rule import RuleExtractor

        self._extractors.append(
            RuleExtractor(model=model, auto_download_model=auto_download_model)
        )
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

    def verify(self, verifier: ProcessingStage) -> 'UnifiedPipeline':
        """Adds VerificationStage"""
        self._stages.append(verifier)
        return self

    def report(
        self,
        config: Optional[ReportConfig] = None,
        quality_config: Optional[QualityConfig] = None
    ) -> 'UnifiedPipeline':
        """Adds ReportStage - generates reports + exports"""
        report_config = config or ReportConfig(exporters=["json"])
        stage = ReportStage(report_config, quality_config if quality_config else QualityConfig())
        self._stages.append(stage)
        return self

    def stage(self, stage: ProcessingStage) -> 'UnifiedPipeline':
        """Adds custom stage"""
        self._stages.append(stage)
        return self

    # ==================== Execute ====================================

    @timeit
    async def run(
        self,
        text: str,
        progress_callback: Optional[ProgressCallback] = None
    ) -> StageResultStream:
        """Execute pipeline (str -> TextEntityStream | MatchResultStream | List[Report])"""
        logger.info(f"Running pipeline with {len(self._extractors)} extractors + {len(self._stages)} stages")

        if not self._extractors:
            return Result.err(["No extractors defined"])

        extract_result = await ParallelStage(self._extractors).extract(text)
        if not extract_result.is_ok:
            return extract_result

        total_steps = 1 + len(self._stages)  # extraction + processing stages
        if progress_callback:
            progress_callback(1, total_steps, "extract")

        stream = extract_result.value
        for i, stage in enumerate(self._stages):
            logger.debug(f"Stage {i+1}/{len(self._stages)}: {stage.__class__.__name__}")
            if progress_callback:
                progress_callback(i + 2, total_steps, stage.__class__.__name__)

            stage_result = await stage.process(stream)
            if not stage_result.is_ok:
                logger.error(f"Stage failed: {stage_result.errors}")
                return stage_result

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

    @timeit
    async def run_and_collect(
        self,
        text: str,
        progress_callback: Optional[ProgressCallback] = None
    ) -> PipelineResult:
        """Convenience: gather results into list"""
        result = await self.run(text, progress_callback=progress_callback)
        if not result.is_ok:
            return Result.err(result.errors)

        final_value = result.value

        if hasattr(final_value, 'to_list'):
            collect_result = await final_value.to_list()
            if not collect_result.is_ok:
                return Result.err(collect_result.errors)
            return Result.ok(collect_result.value)

        if isinstance(final_value, list):
            return Result.ok(final_value)

        return Result.ok([final_value])


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

    fuzzy_stage = FuzzyVerificationStage(source, **VerifierConfig().get_effective_params(verifier_type="fuzzy"))

    # Pipeline without reporting ---------------------------------------------
    # result = await (pipeline()
    #     .with_rules(model='ru_core_news_sm')
    #     # .normalize()
    #     .verify(fuzzy_stage)
    #     .run_and_collect(text))
    # if result.is_ok:
    #     stream = result.value
    #     for entity in stream:
    #         pprint(entity)
    #     return
    # else:
    #     pprint(f"Pipeline failed: {result.errors}")

    # Pipeline with reporting ------------------------------------------------
    result = await (pipeline()
                    .with_rules(model='ru_core_news_sm')
                    .normalize()
                    .verify(fuzzy_stage)
                    .report(ReportConfig(include=[ReportType.EXTRACTION, ReportType.PROCESSING, ReportType.VERIFICATION, ReportType.ONTOLOGY_UPDATE, ReportType.QUALITY_GATE]))
                    .run_and_collect(text))

    if result.is_ok:
        reports = result.value
        print(f"Generated {len(reports)} reports:")

        for report in reports:
            assert isinstance(report, Report)
            data = report.to_dict()
            pprint(data)


if __name__ == "__main__":
    asyncio.run(demo())
