from termlint.core.models import MatchStatus, TextEntity
from termlint.verifier.stages.exact import ExactVerificationStage
from termlint.core.types import TextEntityStream


class TestExactVerificationStage:

    async def test_verification_stage_matched_term(self, initialized_json_glossary, sample_text_entity):
        """Checks exact match"""
        matched_entity = TextEntity(
            text="нейронная сеть",
            original_text="нейронная сеть",
            lemma="нейронная сеть",
            span=(0, 12),
            score=0.95
        )
        stream = TextEntityStream.from_list([matched_entity])

        stage = ExactVerificationStage(initialized_json_glossary)
        result = await stage.process(stream)

        assert result.is_ok
        matches_result = await result.value.to_list()
        assert matches_result.is_ok, f"to_list failed: {matches_result.errors}"

        matches = matches_result.value
        assert len(matches) == 1

        first_match = matches[0]
        assert first_match.status == MatchStatus.MATCHED
        assert first_match.entity is not None
        assert first_match.entity.id == "ml:001"
        assert first_match.confidence == 1.0

    async def test_verification_stage_unknown_term(self, initialized_json_glossary):
        """Check match for unknown term"""
        unknown_entity = TextEntity(
            text="кот",
            original_text="Это был большой и черный кот!",
            lemma="кот",
            span=(0, 5),
            score=0.3
        )
        stream = TextEntityStream.from_list([unknown_entity])

        stage = ExactVerificationStage(initialized_json_glossary)
        result = await stage.process(stream)

        assert result.is_ok
        matches = await result.value.to_list()
        first_entity = matches.value[0]
        assert first_entity.status == MatchStatus.UNKNOWN
        assert first_entity.confidence == 0.0
        assert first_entity.entity is None

    async def test_verification_batch(self, initialized_json_glossary):
        """Check batch match ideal"""
        entities = [
            TextEntity(text="нейронная сеть", original_text="", lemma="нейронная сеть", score=0.95, span=(0,12)),  # find
            TextEntity(text="микросервис", original_text="", lemma="микросервис", score=0.85, span=(13,24)),       # find
            TextEntity(text="кот", original_text="", lemma="кот", score=0.3, span=(25,30))                         # unknown
        ]
        stream = TextEntityStream.from_list(entities)

        stage = ExactVerificationStage(initialized_json_glossary)
        result = await stage.process(stream)

        assert result.is_ok
        matches = await result.value.to_list()

        matched = [m for m in matches.value if m.status == MatchStatus.MATCHED]
        unknown = [m for m in matches.value if m.status == MatchStatus.UNKNOWN]

        assert len(matched) == 2
        assert len(unknown) == 1
