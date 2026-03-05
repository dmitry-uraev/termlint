from pathlib import Path
import tomllib
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from termlint.core.models import QualityConfig


class QualityGates(BaseModel):
    min_coverage: float = 90.0
    max_unknown: int = 5
    min_quality_score: float = 0.8

    def to_quality_config(self) -> QualityConfig:
        """Convert to core.models.QualityConfig"""
        return QualityConfig(
            min_coverage=self.min_coverage,
            max_unknown=self.max_unknown,
            min_quality_score=self.min_quality_score
        )


class ExtractionConfig(BaseModel):
    extractors: List[str] = Field(default_factory=lambda: ["rule"])
    rules: Dict[str, Any] = Field(
        default_factory=lambda: {
            "model": "ru_core_news_sm",
            "auto_download_model": False,
        }
    )


class VerifierConfig(BaseModel):
    source: Optional[Path] = None
    type: Literal["exact", "fuzzy"] = "exact"
    fuzzy: Dict[str, Any] = Field(default_factory=dict)
    exact: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def get_fuzzy_defaults(cls) -> Dict[str, Any]:
        """FuzzyVerificationStage defaults"""
        return {
            "threshold": 85,
            "limit": 3,
            "scorer": "token_sort_ratio"
        }

    @classmethod
    def get_exact_defaults(cls) -> Dict[str, Any]:
        """ExactVerificationStage defaults"""
        return {}

    def get_effective_params(self, verifier_type: str) -> Dict[str, Any]:
        """Config + defaults = effective params"""
        defaults = (
            self.get_fuzzy_defaults() if verifier_type == "fuzzy"
            else self.get_exact_defaults()
        )
        user_params = getattr(self, verifier_type, {})
        return {**defaults, **user_params}  # defaults + override


class ReportsConfig(BaseModel):
    include: List[str] = Field(default_factory=lambda: ["verification", "quality_gate"])
    exporters: List[str] = ["json"]


class PipelineConfig(BaseModel):
    stages: List[str] = Field(default_factory=list, validate_default=True)


class LoggingConfig(BaseModel):
    level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = "WARNING"
    log_file: Optional[Path] = None
    fmt: str = "%(asctime)s [%(name)s] %(levelname)-8s %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S"
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5


class TermlintConfig(BaseModel):
    output_dir: Path = Path("reports/")
    quality_gates: QualityGates = Field(default_factory=QualityGates)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    verifier: VerifierConfig = Field(default_factory=VerifierConfig)
    reports: ReportsConfig = Field(default_factory=ReportsConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def from_pyproject(cls, pyproject_path: Path | str = "pyproject.toml") -> 'TermlintConfig':
        path = Path(pyproject_path)
        try:
            with open(path, "rb") as f:
                raw_data = tomllib.load(f).get("tool", {}).get("termlint", {})

            data = {
                "output_dir": Path(raw_data.get("output_dir", "reports/")),
                "quality_gates": raw_data.get("quality_gates", {}),
                "extraction": raw_data.get("extraction", {}),
                "verifier": raw_data.get("verifier", {}),
                "reports": raw_data.get("reports", {}),
                "pipeline": raw_data.get("pipeline", {}),
                "logging": raw_data.get("logging", {}),
            }

            config = cls(**data)

            if config.verifier.type == "fuzzy":
                config.verifier.fuzzy = {**VerifierConfig.get_fuzzy_defaults(), **config.verifier.fuzzy}

            return config

        except FileNotFoundError:
            if path != Path("pyproject.toml"):
                raise
            return cls()
