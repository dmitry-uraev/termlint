"""DEPRECATED: I/O helpers for glossary and report artifacts."""

import json
from pathlib import Path
from typing import Any, List

from termlint.core.models import Entity, TextEntity


def load_suggested_entities_from_report(report_path: Path | str) -> List[TextEntity]:
    """Load ontology update candidates from exported JSON report file."""
    path = Path(report_path)
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    data = payload.get("data", payload)
    suggested = data.get("suggested_entities")
    if not isinstance(suggested, list):
        raise ValueError(
            f"Expected 'suggested_entities' list in report: {path}"
        )

    entities: List[TextEntity] = []
    for item in suggested:
        try:
            span_value = item.get("span", [0, 0])
            if isinstance(span_value, list) and len(span_value) == 2:
                span = (int(span_value[0]), int(span_value[1]))
            else:
                span = (0, 0)

            entities.append(
                TextEntity(
                    text=str(item.get("text", "")),
                    original_text=str(item.get("original_text", item.get("text", ""))),
                    lemma=str(item.get("lemma", item.get("text", ""))),
                    span=span,
                    score=float(item.get("score", 0.0)),
                    pos_tags=list(item.get("pos_tags", [])),
                    sentence=str(item.get("sentence", "")),
                    frequency=int(item.get("frequency", 1)),
                    extractor_type=str(item.get("extractor_type", "")),
                    properties=dict(item.get("properties", {})),
                )
            )
        except Exception as exc:
            raise ValueError(f"Invalid suggested entity shape: {item}") from exc
    return entities


def load_entities_from_glossary(glossary_path: Path | str) -> List[Entity]:
    """Load glossary entities from glossary JSON array."""
    path = Path(glossary_path)
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, list):
        raise ValueError(f"Glossary must be a JSON array: {path}")

    entities: List[Entity] = []
    for item in payload:
        try:
            entities.append(Entity(**item))
        except Exception as exc:
            raise ValueError(f"Invalid glossary entity: {item}") from exc
    return entities


def write_entities_to_glossary(entities: List[Entity], output_path: Path | str) -> Path:
    """Write entities as glossary JSON array."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = [entity.to_dict() for entity in entities]
    with path.open("w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)
    return path


def write_json(payload: Any, output_path: Path | str) -> Path:
    """Write arbitrary JSON payload."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path
