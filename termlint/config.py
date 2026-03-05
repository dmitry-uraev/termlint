import os
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

    @staticmethod
    def _extract_termlint_section(path: Path) -> Dict[str, Any]:
        with path.open("rb") as f:
            raw = tomllib.load(f)
        # Project config: [tool.termlint]
        tool_section = raw.get("tool", {})
        if isinstance(tool_section, dict) and isinstance(tool_section.get("termlint"), dict):
            return tool_section["termlint"]
        # User config: [termlint] (supported for ~/.termlint/config.toml style)
        if isinstance(raw.get("termlint"), dict):
            return raw["termlint"]
        return {}

    @classmethod
    def _from_raw_data(cls, raw_data: Dict[str, Any]) -> "TermlintConfig":
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

    @classmethod
    def from_pyproject(cls, pyproject_path: Path | str = "pyproject.toml") -> 'TermlintConfig':
        path = Path(pyproject_path)
        try:
            return cls._from_raw_data(cls._extract_termlint_section(path))
        except FileNotFoundError:
            if path != Path("pyproject.toml"):
                raise
            return cls()

    @classmethod
    def discover_config_path(
        cls,
        explicit_config: Optional[Path | str] = None,
        start_dir: Path | str | None = None,
    ) -> Optional[Path]:
        if explicit_config:
            return Path(explicit_config)

        # 1) nearest project pyproject.toml with [tool.termlint]
        project_candidate = cls.find_project_pyproject(start_dir=start_dir)
        if project_candidate:
            return project_candidate

        # 2) user-level config files
        for candidate in cls.user_config_candidates():
            if candidate.exists():
                return candidate
        return None

    @classmethod
    def find_project_pyproject(cls, start_dir: Path | str | None = None) -> Optional[Path]:
        current = Path(start_dir) if start_dir else Path.cwd()
        current = current.resolve()
        for directory in (current, *current.parents):
            candidate = directory / "pyproject.toml"
            if not candidate.exists():
                continue
            try:
                raw_section = cls._extract_termlint_section(candidate)
            except Exception:
                continue
            if raw_section:
                return candidate
        return None

    @classmethod
    def user_config_candidates(cls) -> List[Path]:
        candidates: List[Path] = []
        home = Path.home()
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        appdata = os.environ.get("APPDATA")

        if xdg_config_home:
            candidates.append(Path(xdg_config_home) / "termlint" / "config.toml")
        candidates.append(home / ".config" / "termlint" / "config.toml")
        if appdata:
            candidates.append(Path(appdata) / "termlint" / "config.toml")
        candidates.append(home / ".termlint" / "config.toml")
        return candidates

    @classmethod
    def from_discovery(
        cls,
        explicit_config: Optional[Path | str] = None,
        start_dir: Path | str | None = None,
    ) -> "TermlintConfig":
        config_path = cls.discover_config_path(
            explicit_config=explicit_config,
            start_dir=start_dir,
        )
        if config_path is None:
            return cls()
        return cls.from_pyproject(config_path)
