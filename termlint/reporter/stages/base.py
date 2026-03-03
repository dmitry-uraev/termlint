import asyncio
import pprint
from typing import Dict, List, Optional, Union

from termlint.core.models import MatchResult, MatchStatus, QualityConfig, Report, ReportConfig, ReportType, TextEntity
from termlint.core.stages import ProcessingStage
from termlint.core.types import Result, TextEntityStream, MatchResultStream


class ReportStage(ProcessingStage[Union[TextEntityStream, MatchResultStream], List[Report]]):
    """
    Universal ReportStage - handles all report types from any pipeline position.

    Input: TextEntityStream | MatchResultStream
    Output: List[Report] + exported files + quality gates
    """
    def __init__(
            self,
            config: Optional[ReportConfig] = None,
            quality_config: Optional[QualityConfig] = None
    ) -> None:
        self.config = config or ReportConfig()
        self.quality_config = quality_config or QualityConfig()

    async def process(
        self,
        stream: Union[TextEntityStream, MatchResultStream],
        # context: Optional[Any] = None
    ) -> Result[List[Report]]:
        if isinstance(stream, TextEntityStream):
            items_result = await stream.to_list()
            if not items_result.is_ok:
                return Result.err(items_result.errors)
            reports = await self._generate_extraction_reports(items_result.value)
        else:
            items_result = await stream.to_list()
            if not items_result.is_ok:
                return Result.err(items_result.errors)
            reports = self._generate_verification_reports(items_result.value)

        if not reports:
            return Result.err(["No reports generated"])

        filtered_reports = self._filter_reports(reports, self.config.include)

        if ReportType.QUALITY_GATE in self.config.include:
            quality_report = self._generate_quality_gate(filtered_reports)
            filtered_reports.append(quality_report)

        await self._export_reports(filtered_reports)

        return Result.ok(filtered_reports)

    def _filter_reports(
        self,
        reports: List[Report],
        include: List[ReportType]
    ) -> List[Report]:
        """
        Filter reports by by requested types
        """
        if not include:
            return reports
        return [r for r in reports if r.report_type in include]

    async def _export_reports(self, reports: List[Report]):
        """
        Export reports using configured exporters
        """
        if not self.config.exporters:
            return

        from termlint.reporter.exporters.json import JSONExporter
        exporters = {
            "json": JSONExporter(),
            # TODO: html, junit, etc.
        }

        tasks = []
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        for report in reports:
            for exporter_name in self.config.exporters:
                if exporter_name in exporters:
                    exporter = exporters[exporter_name]
                    filepath = output_dir / f"{report.report_type.value}.{exporter_name}"
                    tasks.append(exporter.export(report, str(filepath)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # Extraction reports -----------------------------------------------------

    async def _generate_extraction_reports(self, entities: List[TextEntity]) -> List[Report]:
        reports = []

        extraction_report = Report(
            report_type=ReportType.EXTRACTION,
            total_items=len(entities),
            processed_items=len(entities),
            raw_data={
                "extractor_stats": self._extractor_stats(entities),
                "score_distribution": self._score_stats(entities)
            }
        )
        reports.append(extraction_report)
        return reports

    # Verification reports ---------------------------------------------------

    def _generate_verification_reports(self, matches: List[MatchResult]) -> List[Report]:
        reports = []

        total = len(matches)

        # successful match includes MATCHED + NEAR MATCHED
        matched = len([m for m in matches if m.status in (MatchStatus.MATCHED, MatchStatus.NEAR_MATCH)])
        coverage_pct = (matched / total * 100) if total > 0 else 0

        # high score for quality analysis
        high_score_unknown = [
            m.text_entity for m in matches
            if m.status == MatchStatus.UNKNOWN and m.text_entity.score >= 0.8
        ]

        verification_report = Report(
            report_type=ReportType.VERIFICATION,
            total_items=total,
            processed_items=matched,
            coverage_pct=coverage_pct,
            unknown_terms=high_score_unknown,
            matches=matches,
            quality_score=self._calculate_quality_score(matches)
        )
        reports.append(verification_report)


        # all unknown for ontology update report
        all_unknown = [m.text_entity for m in matches if m.status == MatchStatus.UNKNOWN]

        if all_unknown:
            ontology_report = Report(
                report_type=ReportType.ONTOLOGY_UPDATE,
                total_items=total,
                processed_items=len(all_unknown),
                suggested_entities=all_unknown,
                # raw_data={"score_threshold": None} # TODO: inspect if threshold is required for ontology update
            )
            reports.append(ontology_report)

        return reports

    def _generate_quality_gate(self, reports):
        """Generate QUALITY_GATE report"""
        quality_pass = self.quality_config.check(reports)
        exit_code = 0 if quality_pass else 1

        verification_report = next((r for r in reports if r.report_type == ReportType.VERIFICATION), None)
        total_items = verification_report.total_items if verification_report else 0
        processed_items = verification_report.processed_items if verification_report else 0

        return Report(
            report_type=ReportType.QUALITY_GATE,
            total_items=total_items,
            processed_items=processed_items,
            quality_pass=quality_pass,
            exit_code=exit_code,
            raw_data={"source_reports": [r.report_type.value for r in reports]}
        )


    # Helpers ----------------------------------------------------------------

    def _extractor_stats(self, entities: List[TextEntity]) -> Dict[str, int]:
        """Stats by extractor"""
        from collections import Counter
        return dict(Counter(e.extractor_type for e in entities))

    def _score_stats(self, entities: List[TextEntity]) -> Dict[str, float]:
        """Score distribution"""
        if not entities:
            return {}

        scores = [e.score for e in entities]
        return {
            "avg_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores)
        }

    def _calculate_quality_score(self, matches: List[MatchResult]) -> float:
        """Weighted quality score"""
        matched = [m.confidence for m in matches if m.status == MatchStatus.MATCHED]
        if not matched:
            return 0.0
        return sum(matched) / len(matched)


async def test_report_stage():
    """All-in-one test"""

    text_entities = [
        TextEntity(
            text="нейросеть", original_text="нейросеть", lemma="нейросеть",
            span=(10, 20), score=0.95, extractor_type="rule"
        ),
        TextEntity(text="токен", original_text="токен", lemma="токен",
                   span=(0, 0), score=0.85, extractor_type="cvalue")
    ]

    match_results = [
        MatchResult(
            text_entity=text_entities[0],
            entity=None, confidence=0.0, status=MatchStatus.UNKNOWN
        ),
        MatchResult(
            text_entity=text_entities[1],
            entity=None, confidence=0.0, status=MatchStatus.UNKNOWN
        ),
        MatchResult(
            text_entity=TextEntity(text="нейрон", original_text="нейрон", lemma="нейрон", span=(0, 0), score=0.75, extractor_type="rule"),
            entity=None, confidence=0.0, status=MatchStatus.MATCHED  # 1 matched
        )
    ]

    entity_stream = TextEntityStream.from_list(text_entities)
    match_stream = MatchResultStream.from_list(match_results)

    print("=== EXTRACTION REPORT ===")
    stage = ReportStage(ReportConfig(exporters=[], include=[ReportType.EXTRACTION]))
    result = await stage.process(entity_stream)
    print("Status:", "OK" if result.is_ok else "ERROR")
    print("Reports:", len(result.value) if result.is_ok else result.errors)
    pprint.pprint(result.value[0].to_dict())

    print("\n=== VERIFICATION REPORTS ===")
    stage = ReportStage(ReportConfig(exporters=[], include=[ReportType.VERIFICATION, ReportType.ONTOLOGY_UPDATE]))
    result = await stage.process(match_stream)
    if result.is_ok:
        for report in result.value:
            print(f"{report.report_type.value}: coverage={getattr(report, 'coverage_pct', 'N/A')}")
            pprint.pprint(report.to_dict())
    else:
        print("Errors:", result.errors)

    print("\n=== QUALITY GATE FAIL ===")
    config = ReportConfig(include=[ReportType.VERIFICATION, ReportType.QUALITY_GATE])
    stage = ReportStage(config, QualityConfig(min_coverage=95.0))
    result = await stage.process(match_stream)

    if result.is_ok:
        # здесь бы ты получил список Report, включая QUALITY_GATE
        for r in result.value:
            print(r.report_type, r.to_dict())
    else:
        print("Quality gate:", "FAIL", result.errors)


if __name__ == "__main__":
    asyncio.run(test_report_stage())
