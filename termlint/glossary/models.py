"""Domain models for glossary conversion and merge."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class MatchPolicy(str, Enum):
    SKIP = "skip"
    MERGE_SYNONYMS = "merge-synonyms"
    REPLACE = "replace"


class ConflictPolicy(str, Enum):
    KEEP_BASE = "keep-base"
    KEEP_UPDATE = "keep-update"
    REPORT = "report"


@dataclass(frozen=True)
class MergePolicy:
    on_match: MatchPolicy = MatchPolicy.MERGE_SYNONYMS
    on_conflict: ConflictPolicy = ConflictPolicy.REPORT


@dataclass(frozen=True)
class MergeConflict:
    conflict_type: str
    message: str
    base_id: str | None = None
    update_id: str | None = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_type": self.conflict_type,
            "message": self.message,
            "base_id": self.base_id,
            "update_id": self.update_id,
            "raw_data": self.raw_data,
        }


@dataclass(frozen=True)
class MergeSummary:
    added: int = 0
    updated: int = 0
    skipped: int = 0
    conflicts: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "added": self.added,
            "updated": self.updated,
            "skipped": self.skipped,
            "conflicts": self.conflicts,
        }


@dataclass(frozen=True)
class MergeResult:
    merged: List[dict]
    conflicts: List[MergeConflict]
    summary: MergeSummary
