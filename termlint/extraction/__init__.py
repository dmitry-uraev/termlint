"""TextEntityStream -> TextEntityStream processing stages."""
from typing import TYPE_CHECKING, Any

from termlint.extraction.stages.base import ExtractionStage
from termlint.extraction.stages.normalize import NormalizationStage
from termlint.extraction.stages.parallel import ParallelStage

from termlint.extraction.extractors.base import BaseExtractor, ConfigurableExtractor

if TYPE_CHECKING:
    from termlint.extraction.extractors.cvalue import CValueExtractor
    from termlint.extraction.extractors.rule import RuleExtractor

__all__ = [
    "ExtractionStage",
    "NormalizationStage",
    "ParallelStage",
    "BaseExtractor",
    "ConfigurableExtractor",
    "RuleExtractor",
    "CValueExtractor",
]


def __getattr__(name: str) -> Any:
    if name == "RuleExtractor":
        try:
            from termlint.extraction.extractors.rule import RuleExtractor
        except Exception as exc:
            raise ImportError(
                "RuleExtractor is unavailable because spaCy failed to import in this environment."
            ) from exc
        return RuleExtractor

    if name == "CValueExtractor":
        from termlint.extraction.extractors.cvalue import CValueExtractor
        return CValueExtractor

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
