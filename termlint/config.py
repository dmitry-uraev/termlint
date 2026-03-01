from pathlib import Path
import tomllib
from typing import Any, Dict, List

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
    rules: Dict[str, Any] = Field(default_factory=lambda: {"model": "ru_core_news_sm"})


class VerifierConfig(BaseModel):
    sources: List[str] = Field(default_factory=lambda: ["json_glossary"])
    exact: bool = True
    fuzzy: Dict[str, Any] = Field(default_factory=lambda: {"threshold": 85, "limit": 5})


class ReportsConfig(BaseModel):
    include: List[str] = Field(default_factory=lambda: ["verification", "quality_gate"])
    exporters: List[str] = ["json"]


class PipelineConfig(BaseModel):
    stages: List[str] = Field(default_factory=list, validate_default=True)


class TermlintConfig(BaseModel):
    source: Path = Path("glossary.json")
    output_dir: Path = Path("reports/")
    quality_gates: QualityGates = Field(default_factory=QualityGates)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    verifier: VerifierConfig = Field(default_factory=VerifierConfig)
    reports: ReportsConfig = Field(default_factory=ReportsConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)

    @classmethod
    def from_pyproject(cls) -> 'TermlintConfig':
        try:
            with open("pyproject.toml", "rb") as f:
                data = tomllib.load(f).get("tool", {}).get("termlint", {})

            if "pipeline" in data and "stages" in data["pipeline"]:
                data["pipeline"]["stages"] = data["pipeline"]["stages"]
            return cls(**data)
        except FileNotFoundError:
            return cls()
