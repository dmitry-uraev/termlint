from unittest.mock import AsyncMock, MagicMock

from typing import Optional

import pytest
from termlint.core.types import Result, TextEntityStream
from termlint.extraction.stages.base import ExtractionStage


@pytest.fixture
def sample_stream(sample_text_entity) -> TextEntityStream:
    return TextEntityStream.from_list([sample_text_entity])


class DummyStage(ExtractionStage):

    def __init__(self, next_stage = None, handle_result: Optional[Result[TextEntityStream]] = None):
        super().__init__(next_stage)
        self.input_stream = None
        self.handle_result = handle_result or Result.ok(TextEntityStream.from_list([]))

    async def _handle(self, stream: TextEntityStream) -> Result[TextEntityStream]:
        self.input_stream = stream
        return self.handle_result


async def test_base_stage_single_stage_ok(sample_stream) -> None:
    """Test that a single stage processes the stream correctly and returns an ok result"""
    stage = DummyStage()

    result = await stage.process(sample_stream)

    assert result.is_ok
    assert result.value is not None
    assert stage.input_stream == sample_stream


async def test_base_stage_chain_ok_propagation(sample_stream) -> None:
    """Test that a stage correctly invokes the next stage in the chain when the result is ok"""
    next_stage = MagicMock(spec=ExtractionStage)
    next_stage.process = AsyncMock(return_value=Result.ok(TextEntityStream.from_list([])))

    chain = DummyStage(next_stage=next_stage)
    result = await chain.process(sample_stream)

    assert result.is_ok
    next_stage.process.assert_called_once()


async def test_base_stage_chain_error_propagation_stops_chain(sample_stream) -> None:
    """Test that a stage correctly propagates an error result and does not invoke the next stage in the chain"""
    error_message = "Error in _handle does not invoke next stage"

    next_stage = MagicMock(spec=ExtractionStage)
    chain = DummyStage(
        handle_result=Result.err([error_message]),
        next_stage=next_stage
    )
    result = await chain.process(sample_stream)

    assert not result.is_ok
    assert result.errors == [error_message]
    next_stage.process.assert_not_called()


async def test_base_stage_last_stage_returns_result(sample_text_entity) -> None:
    """Test that the last stage in the chain returns the expected result when processing is successful"""
    expected_stream = TextEntityStream.from_list([sample_text_entity])
    final_stage = DummyStage(handle_result=Result.ok(expected_stream))

    input_stream = TextEntityStream.from_list([])
    result = await final_stage.process(input_stream)

    assert result.is_ok
    assert result.value is not None

    entities = await result.value.to_list()
    assert len(entities.value) == 1
    assert entities.value[0] == sample_text_entity
