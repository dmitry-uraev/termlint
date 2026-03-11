"""
Tests suite for termlint.entity_building.selectors module
"""

from termlint.core.models import MatchResult, MatchStatus
from termlint.entity_building.selectors import PassThroughTextSelector, UnknownMatchSelector
from termlint.core.types import TextEntityStream, MatchResultStream


async def test_pass_through_text_selector_passes_entities(sample_text_entity):
    """Check that pass through text selector preservers and returns all entities from source stream"""
    stream = TextEntityStream.from_list([sample_text_entity])
    selector = PassThroughTextSelector()

    selected_stream_result = await selector.select(stream)

    assert selected_stream_result.ok
    assert isinstance(selected_stream_result.value, TextEntityStream)

    selected_entities = (await selected_stream_result.value.to_list()).value

    assert len(selected_entities) == 1
    assert selected_entities[0] is sample_text_entity

async def test_unknown_match_selector_filters_other_statuses(sample_text_entity):
    """Checks that unknown match selector outputs only unknown matched results"""

    stream = MatchResultStream.from_list([
        MatchResult(text_entity=sample_text_entity, status=MatchStatus.MATCHED),
        MatchResult(text_entity=sample_text_entity, status=MatchStatus.NEAR_MATCH),
        MatchResult(text_entity=sample_text_entity, status=MatchStatus.AMBIGUOUS),
        MatchResult(text_entity=sample_text_entity, status=MatchStatus.UNKNOWN)
    ])

    selector = UnknownMatchSelector()

    selected_stream_result = await selector.select(stream)

    assert selected_stream_result.ok
    assert isinstance(selected_stream_result.value, MatchResultStream)

    selected_entities = (await selected_stream_result.value.to_list()).value

    assert len(selected_entities) == 1
    assert selected_entities[0].status == MatchStatus.UNKNOWN
