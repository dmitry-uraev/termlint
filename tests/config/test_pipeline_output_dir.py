from pathlib import Path

from termlint.pipeline import UnifiedPipeline
from termlint.reporter.stages.base import ReportStage
from termlint.config import TermlintConfig


async def test_from_config_applies_output_dir_to_report_stage(tmp_path: Path):
    cfg = tmp_path / "pyproject.toml"
    cfg.write_text(
        """
[tool.termlint]
output_dir = "custom_reports"

[tool.termlint.extraction]
extractors = ["cvalue"]
cvalue = { use_ling_filter = false, threshold = 0.0 }

[tool.termlint.verifier]
type = "exact"
source = "tests/fixtures/test_glossary.json"

[tool.termlint.reports]
include = ["ontology_update"]
exporters = ["json"]

[tool.termlint.pipeline]
stages = ["extract", "verify", "report"]
""".strip(),
        encoding="utf-8",
    )

    config = TermlintConfig.from_pyproject(cfg)
    pipeline = await UnifiedPipeline.from_config(config)

    report_stage = next(stage for stage in pipeline._stages if isinstance(stage, ReportStage))
    assert report_stage.config.output_dir == Path("custom_reports")
