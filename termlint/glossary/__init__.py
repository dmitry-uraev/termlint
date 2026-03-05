"""Glossary generation and merge utilities."""

from termlint.glossary.converter import convert_candidates_to_entities
from termlint.glossary.io import (
    load_entities_from_glossary,
    load_suggested_entities_from_report,
    write_entities_to_glossary,
    write_json,
)
from termlint.glossary.merge import merge_entities
from termlint.glossary.models import MergeConflict, MergePolicy, MergeSummary

__all__ = [
    "convert_candidates_to_entities",
    "load_entities_from_glossary",
    "load_suggested_entities_from_report",
    "write_entities_to_glossary",
    "write_json",
    "merge_entities",
    "MergeConflict",
    "MergePolicy",
    "MergeSummary",
]
