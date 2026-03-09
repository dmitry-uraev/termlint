from pathlib import Path

from termlint.config import TermlintConfig
from termlint.extraction.extractors.cvalue import CValueExtractor
from termlint.extraction.extractors.cvalue_support.config import (
    DEFAULT_AUTO_MODEL_DOWNLOAD,
    DEFAULT_MAX_LENGTH,
    DEFAULT_MIN_FREQ,
    DEFAULT_MIN_LENGTH,
    DEFAULT_MODEL,
    DEFAULT_THRESHOLD,
    DEFAULT_USE_LING_FILTER,
)
from termlint.pipeline import UnifiedPipeline


def test_extraction_defaults_include_cvalue():
    config = TermlintConfig()

    assert config.extraction.extractors == ["rule", "cvalue"]
    assert config.extraction.cvalue == {
        "threshold": DEFAULT_THRESHOLD,
        "min_freq": DEFAULT_MIN_FREQ,
        "min_length": DEFAULT_MIN_LENGTH,
        "max_length": DEFAULT_MAX_LENGTH,
        "use_ling_filter": DEFAULT_USE_LING_FILTER,
        "model": DEFAULT_MODEL,
        "auto_download_model": DEFAULT_AUTO_MODEL_DOWNLOAD,
    }


def test_from_pyproject_reads_cvalue_config(tmp_path: Path):
    cfg = tmp_path / "pyproject.toml"
    cfg.write_text(
        """
[tool.termlint.extraction]
extractors = ["cvalue"]
cvalue = { threshold = 0.5, min_freq = 2, min_length = 2, max_length = 3, use_ling_filter = false, model = "en_core_web_sm", auto_download_model = false }
""".strip(),
        encoding="utf-8",
    )

    config = TermlintConfig.from_pyproject(cfg)
    assert config.extraction.extractors == ["cvalue"]
    assert config.extraction.cvalue["threshold"] == 0.5
    assert config.extraction.cvalue["min_freq"] == 2
    assert config.extraction.cvalue["max_length"] == 3
    assert config.extraction.cvalue["use_ling_filter"] is False
    assert config.extraction.cvalue["model"] == "en_core_web_sm"
    assert config.extraction.cvalue["auto_download_model"] is False

async def test_pipeline_from_config_builds_cvalue_extractor(tmp_path: Path):
    cfg = tmp_path / "pyproject.toml"
    cfg.write_text(
        """
[tool.termlint.extraction]
extractors = ["cvalue"]
cvalue = { threshold = 0.7, min_freq = 2, min_length = 2, max_length = 3, use_ling_filter = false, model = "ru_core_news_sm", auto_download_model = false }

[tool.termlint.pipeline]
stages = ["extract"]
""".strip(),
        encoding="utf-8",
    )

    config = TermlintConfig.from_pyproject(cfg)
    pipeline = await UnifiedPipeline.from_config(config)

    assert len(pipeline._extractors) == 1
    assert isinstance(pipeline._extractors[0], CValueExtractor)
    extractor = pipeline._extractors[0]
    assert extractor.threshold == 0.7
    assert extractor.min_freq == 2
    assert extractor.max_length == 3
    assert extractor.use_ling_filter is False
