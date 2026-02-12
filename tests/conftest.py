import pytest

from termlint.core.models import TextEntity


@pytest.fixture
async def sample_text_entity():
    return TextEntity(
        text="entity",
        original_text="Sample original text with entity",
        lemma="entity",
        span=(26, 31),
        score=0.9
    )
