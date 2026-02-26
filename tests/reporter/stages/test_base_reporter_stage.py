import json
from pathlib import Path

import pytest

from termlint.core.models import QualityConfig, ReportConfig, ReportType
from termlint.core.types import MatchResultStream, TextEntityStream
from termlint.reporter.stages.base import ReportStage


async def test_extraction_report_basic(text_entities_to_report, tmp_path: Path):
    # TODO: split
    stream = TextEntityStream.from_list(text_entities_to_report)

    stage = ReportStage(
        ReportConfig(
            include=[ReportType.EXTRACTION],
            exporters=["json"],
            output_dir=tmp_path,
        )
    )

    result = await stage.process(stream)
    assert result.is_ok

    reports = result.value
    assert len(reports) == 1

    report = reports[0]
    data = report.to_dict()

    # Check base metrics
    assert report.report_type is ReportType.EXTRACTION
    assert data["total_items"] == 2
    assert data["processed_items"] == 2

    # Statistics by extractor_type
    extractor_stats = data["raw_data"]["extractor_stats"]
    assert extractor_stats == {"rule": 1, "cvalue": 1}

    # Statistics by score
    score_dist = data["raw_data"]["score_distribution"]
    assert score_dist["min_score"] == 0.85
    assert score_dist["max_score"] == 0.95
    assert score_dist["avg_score"] == pytest.approx(0.9)

    # Check JSON file actually created
    json_path = tmp_path / "extraction.json"
    assert json_path.exists()

    with json_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    assert payload["metadata"]["report_type"] == "extraction"
    assert payload["data"]["total_items"] == 2


async def test_verification_and_ontology_reports(match_results_to_report, tmp_path: Path):
    stream = MatchResultStream.from_list(match_results_to_report)

    stage = ReportStage(
        ReportConfig(
            include=[ReportType.VERIFICATION, ReportType.ONTOLOGY_UPDATE],
            exporters=["json"],
            output_dir=tmp_path,
        )
    )

    result = await stage.process(stream)
    assert result.is_ok

    reports = sorted(result.value, key=lambda r: r.report_type.value)
    assert {r.report_type for r in reports} == {
        ReportType.VERIFICATION,
        ReportType.ONTOLOGY_UPDATE,
    }

    verification = next(r for r in reports if r.report_type is ReportType.VERIFICATION)
    ontology = next(r for r in reports if r.report_type is ReportType.ONTOLOGY_UPDATE)

    v = verification.to_dict()
    o = ontology.to_dict()

    # VERIFICATION: 1 out of 3 matched
    assert v["total_items"] == 3
    assert v["processed_items"] == 1
    assert v["coverage_pct"] == pytest.approx(100.0 / 3.0, rel=1e-6)

    # unknown_terms - 2 high-score UNKNOWN
    assert len(v["unknown_terms"]) == 2
    assert {t["text"] for t in v["unknown_terms"]} == {"нейросеть", "токен"}

    # ONTOLOGY_UPDATE: same suggested_entities
    assert o["total_items"] == 3
    assert o["processed_items"] == 2
    assert len(o["suggested_entities"]) == 2
    assert {t["text"] for t in o["suggested_entities"]} == {"нейросеть", "токен"}
    # assert o["raw_data"]["score_threshold"] == 0.8

    # Check file exists
    verification_path = tmp_path / "verification.json"
    ontology_path = tmp_path / "ontology_update.json"

    assert verification_path.exists()
    assert ontology_path.exists()


async def test_quality_gate_fail(match_results_to_report, tmp_path: Path):
    stream = MatchResultStream.from_list(match_results_to_report)

    # Strict coverage threshold to get FAIL
    stage = ReportStage(
        ReportConfig(
            include=[ReportType.VERIFICATION, ReportType.QUALITY_GATE],
            exporters=["json"],
            output_dir=tmp_path,
        ),
        QualityConfig(min_coverage=95.0),
    )

    result = await stage.process(stream)
    assert result.is_ok  # stage should not fail

    reports = result.value
    assert {r.report_type for r in reports} == {
        ReportType.VERIFICATION,
        ReportType.QUALITY_GATE,
    }

    quality_report = next(r for r in reports if r.report_type is ReportType.QUALITY_GATE)
    q = quality_report.to_dict()

    assert q["quality_pass"] is False
    assert q["exit_code"] == 1

    gate_path = tmp_path / "quality_gate.json"
    assert gate_path.exists()

    with gate_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    assert payload["metadata"]["report_type"] == "quality_gate"
    assert payload["data"]["quality_pass"] is False
    assert payload["data"]["exit_code"] == 1


async def test_quality_gate_pass(match_results_to_report, tmp_path: Path):
    stream = MatchResultStream.from_list(match_results_to_report)

    # Lower threshold to pass with 33.33%
    stage = ReportStage(
        ReportConfig(
            include=[ReportType.VERIFICATION, ReportType.QUALITY_GATE],
            exporters=[],  # no exporters required
            output_dir=tmp_path,
        ),
        QualityConfig(min_coverage=30.0),
    )

    result = await stage.process(stream)
    assert result.is_ok

    reports = result.value
    quality_report = next(r for r in reports if r.report_type is ReportType.QUALITY_GATE)
    q = quality_report.to_dict()

    assert q["quality_pass"] is True
    assert q["exit_code"] == 0


async def test_no_quality_gate_if_not_included(match_results_to_report, tmp_path: Path):
    stream = MatchResultStream.from_list(match_results_to_report)

    stage = ReportStage(
        ReportConfig(
            include=[ReportType.VERIFICATION],
            exporters=["json"],
            output_dir=tmp_path,
        )
    )

    result = await stage.process(stream)
    assert result.is_ok

    reports = result.value
    types = {r.report_type for r in reports}
    assert ReportType.QUALITY_GATE not in types
    assert ReportType.VERIFICATION in types

    assert not (tmp_path / "quality_gate.json").exists()
