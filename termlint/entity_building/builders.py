from termlint.core.types import EntityStream, MatchResultStream, Result, TextEntityStream


class DefaultTextEntityBuilder:
    def __init__(
        self,
        namespace: str = "auto",
        min_score: float = 0.0,
        min_frequency: int = 1,
    ) -> None:
        self.namespace = namespace
        self.min_score = min_score
        self.min_frequency = min_frequency

    async def build(self, stream: TextEntityStream) -> Result[EntityStream]:
        ...


class DefaultMatchResultEntityBuilder:
    """
    Implementation detail: DefaultMatchResultEntityBuilder will likely
        transform selected MatchResult items into TextEntity candidates
        first, then reuse the same normalization logic as the text builder.
    """
    def __init__(
        self,
        namespace: str = "auto",
        min_score: float = 0.0,
        min_frequency: int = 1,
    ) -> None:
        self.namespace = namespace
        self.min_score = min_score
        self.min_frequency = min_frequency

    async def build(self, stream: MatchResultStream) -> Result[EntityStream]:
        ...
