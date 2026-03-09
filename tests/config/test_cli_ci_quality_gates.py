from pathlib import Path

from click.testing import CliRunner

from termlint.cli import cli
from termlint.config import VerifierConfig
from termlint.core.models import Report, ReportType
from termlint.core.types import Result


def test_verify_applies_quality_gate_overrides(monkeypatch):
    runner = CliRunner()
    called = {"checked": False}

    async def fake_build_pipeline_or_exit(config):
        assert config.quality_gates.min_coverage == 77.5
        assert config.quality_gates.max_unknown == 11
        assert config.quality_gates.min_quality_score == 0.42
        called["checked"] = True
        return object()

    async def fake_run_pipeline_for_file_or_exit(pipeline, file_path: Path, progress_callback):
        report = Report(
            report_type=ReportType.QUALITY_GATE,
            total_items=1,
            processed_items=1,
            quality_pass=True,
            exit_code=0,
        )
        return Result.ok([report])

    monkeypatch.setattr("termlint.cli.build_pipeline_or_exit", fake_build_pipeline_or_exit)
    monkeypatch.setattr("termlint.cli.run_pipeline_for_file_or_exit", fake_run_pipeline_for_file_or_exit)

    with runner.isolated_filesystem():
        Path("in.txt").write_text("test text", encoding="utf-8")
        Path("glossary.json").write_text("[]", encoding="utf-8")

        result = runner.invoke(
            cli,
            [
                "verify",
                "in.txt",
                "--source",
                "glossary.json",
                "--min-coverage",
                "77.5",
                "--max-unknown",
                "11",
                "--min-quality-score",
                "0.42",
            ],
        )

    assert result.exit_code == 0, result.output
    assert called["checked"] is True


def test_verify_fail_on_quality_gate_sets_exit_code_1(monkeypatch):
    runner = CliRunner()

    async def fake_build_pipeline_or_exit(config):
        return object()

    async def fake_run_pipeline_for_file_or_exit(pipeline, file_path: Path, progress_callback):
        report = Report(
            report_type=ReportType.QUALITY_GATE,
            total_items=3,
            processed_items=1,
            quality_pass=False,
            exit_code=1,
        )
        return Result.ok([report])

    monkeypatch.setattr("termlint.cli.build_pipeline_or_exit", fake_build_pipeline_or_exit)
    monkeypatch.setattr("termlint.cli.run_pipeline_for_file_or_exit", fake_run_pipeline_for_file_or_exit)

    with runner.isolated_filesystem():
        Path("in.txt").write_text("test text", encoding="utf-8")
        Path("glossary.json").write_text("[]", encoding="utf-8")

        result = runner.invoke(
            cli,
            [
                "verify",
                "in.txt",
                "--source",
                "glossary.json",
                "--fail-on-quality-gate",
            ],
        )

    assert result.exit_code == 1, result.output


def test_verify_quickstart_works_without_config(monkeypatch):
    runner = CliRunner()
    called = {"checked": False}

    async def fake_build_pipeline_or_exit(config):
        assert config.pipeline.stages == ["extract", "normalize", "verify", "report"]
        assert config.extraction.extractors == ["rule", "cvalue"]
        assert config.extraction.rules == {
            "model": "en_core_web_sm",
            "auto_download_model": False,
        }
        assert config.extraction.cvalue["model"] == "en_core_web_sm"
        assert config.reports.include == ["verification", "quality_gate", "ontology_update"]
        assert config.verifier.source == Path("glossary.json")
        assert config.verifier.type == "fuzzy"
        assert config.verifier.fuzzy == {"threshold": 85}
        assert config.verifier.get_effective_params("fuzzy") == {
            **VerifierConfig.get_fuzzy_defaults(),
            "threshold": 85,
        }
        called["checked"] = True
        return object()

    async def fake_run_pipeline_for_file_or_exit(pipeline, file_path: Path, progress_callback):
        assert file_path == Path("input.txt")
        reports = [
            Report(
                report_type=ReportType.VERIFICATION,
                total_items=6,
                processed_items=2,
                coverage_pct=33.3,
                exit_code=0,
            ),
            Report(
                report_type=ReportType.QUALITY_GATE,
                total_items=1,
                processed_items=1,
                quality_pass=False,
                exit_code=0,
            ),
            Report(
                report_type=ReportType.ONTOLOGY_UPDATE,
                total_items=0,
                processed_items=0,
                exit_code=0,
            ),
        ]
        return Result.ok(reports)

    monkeypatch.setattr("termlint.cli.build_pipeline_or_exit", fake_build_pipeline_or_exit)
    monkeypatch.setattr("termlint.cli.run_pipeline_for_file_or_exit", fake_run_pipeline_for_file_or_exit)

    with runner.isolated_filesystem():
        Path("input.txt").write_text(
            "Artificial intelligence and machine learning are used in data analytics.",
            encoding="utf-8",
        )
        Path("glossary.json").write_text(
            '[{"id":"ml:001","label":"machine learning","synonyms":["ML"]}]',
            encoding="utf-8",
        )

        result = runner.invoke(
            cli,
            [
                "verify",
                "input.txt",
                "--source",
                "glossary.json",
                "--verifier",
                "fuzzy",
                "--threshold",
                "85",
            ],
        )

    assert result.exit_code == 0, result.output
    assert called["checked"] is True
