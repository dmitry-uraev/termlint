import pytest

from termlint.core.models import MatchResult, MatchStatus, TextEntity


@pytest.fixture
def text_entities_to_report() -> list[TextEntity]:
    return [
        TextEntity(
            text="нейросеть",
            original_text="нейросеть",
            lemma="нейросеть",
            span=(10, 20),
            score=0.95,
            extractor_type="rule",
        ),
        TextEntity(
            text="токен",
            original_text="токен",
            lemma="токен",
            span=(0, 0),
            score=0.85,
            extractor_type="cvalue",
        ),
    ]

@pytest.fixture
def match_results_to_report(text_entities_to_report: list[TextEntity]) -> list[MatchResult]:
    return [
        MatchResult(
            text_entity=text_entities_to_report[0],
            entity=None,
            confidence=0.0,
            status=MatchStatus.UNKNOWN,
        ),
        MatchResult(
            text_entity=text_entities_to_report[1],
            entity=None,
            confidence=0.0,
            status=MatchStatus.UNKNOWN,
        ),
        MatchResult(
            text_entity=TextEntity(
                text="нейрон",
                original_text="нейрон",
                lemma="нейрон",
                span=(0, 0),
                score=0.75,
                extractor_type="rule",
            ),
            entity=None,
            confidence=0.0,
            status=MatchStatus.MATCHED,
        ),
    ]
