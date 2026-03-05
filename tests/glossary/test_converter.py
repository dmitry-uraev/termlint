from termlint.core.models import TextEntity
from termlint.glossary.converter import convert_candidates_to_entities


def test_convert_candidates_to_entities_deduplicates_by_canonical_key():
    candidates = [
        TextEntity(text="Machine Learning", original_text="Machine Learning", lemma="machine learning", span=(0, 2), score=0.9),
        TextEntity(text="machine  learning", original_text="machine learning", lemma="machine learning", span=(3, 5), score=0.8),
        TextEntity(text="ML", original_text="ML", lemma="ml", span=(6, 7), score=0.95),
    ]

    entities = convert_candidates_to_entities(candidates, namespace="auto", min_score=0.5)
    labels = sorted([e.label for e in entities])

    assert labels == ["machine learning", "ml"]
    ml_entity = next(e for e in entities if e.label == "machine learning")
    assert ml_entity.synonyms == []


def test_convert_candidates_to_entities_respects_thresholds():
    candidates = [
        TextEntity(text="good", original_text="good", lemma="good", span=(0, 1), score=0.7, frequency=2),
        TextEntity(text="low_score", original_text="low_score", lemma="low_score", span=(1, 2), score=0.2, frequency=10),
        TextEntity(text="low_freq", original_text="low_freq", lemma="low_freq", span=(2, 3), score=0.8, frequency=0),
    ]
    entities = convert_candidates_to_entities(
        candidates,
        min_score=0.5,
        min_frequency=1,
    )
    assert len(entities) == 1
    assert entities[0].label == "good"
