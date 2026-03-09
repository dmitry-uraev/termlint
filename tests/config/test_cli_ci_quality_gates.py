from pathlib import Path

from click.testing import CliRunner

from termlint.cli import cli
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
