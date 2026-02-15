"""Unit tests for the base extraction stage implementation"""

from typing import Optional

import pytest
from termlint.core.types import Result, TextEntityStream
from termlint.extraction.stages.base import ExtractionStage


@pytest.fixture
def sample_stream(sample_text_entity) -> TextEntityStream:
    return TextEntityStream.from_list([sample_text_entity])


class DummyStage(ExtractionStage):

    def __init__(self, handle_result: Optional[Result[TextEntityStream]] = None):
        self.input_stream = TextEntityStream.from_list([])
        self.call_count = 0
        self.handle_result = handle_result

    async def _handle(self, stream: TextEntityStream) -> Result[TextEntityStream]:
        self.input_stream = stream
        self.call_count += 1

        if self.handle_result:
            return self.handle_result

        return Result.ok(stream)


async def test_base_extraction_stage_process_calls_handle(sample_stream) -> None:
    """Test that a single stage processes the stream correctly and returns an ok result"""
    stage = DummyStage()

    result = await stage.process(sample_stream)

    assert stage.call_count == 1
    assert stage.input_stream == sample_stream
    assert result.is_ok
    assert result.value is not None


async def test_base_extraction_stage_handle_error_propagation(sample_stream) -> None:
    """Test that errors from _handle() are propagated correctly"""

    error_msg = "Error in _handle method"
    stage = DummyStage(handle_result=Result.err([error_msg]))

    result = await stage.process(sample_stream)

    assert not result.is_ok
    assert result.errors == [error_msg]
    assert stage.input_stream == sample_stream


async def test_base_extraction_stage_preserves_ok_result(sample_stream) -> None:
    """Test that input stream reference is preserved correctly"""

    stage = DummyStage()
    result = await stage.process(sample_stream)

    assert result.is_ok
    entities = await result.value.to_list()
    assert entities.is_ok
    assert len(entities.value) == 1


async def test_base_extraction_stage_called_once(sample_stream) -> None:
    """Test that stage processes input exactly once"""
    stage = DummyStage()

    result = await stage.process(sample_stream)

    assert stage.call_count == 1


async def test_base_extraction_stage_different_inputs(sample_stream) -> None:
    """Test that stage can handle different input streams"""
    stage = DummyStage()

    result1 = await stage.process(sample_stream)
    result2 = await stage.process(TextEntityStream.from_list([]))

    assert stage.call_count == 2
    assert result1.is_ok and result2.is_ok

    entities1 = await result1.value.to_list()
    entities2 = await result2.value.to_list()

    assert len(entities1.value) == 1    # first call should return the sample entity
    assert len(entities2.value) == 0    # second call should return empty stream
