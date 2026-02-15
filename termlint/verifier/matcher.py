"""
Terminology matching logic between TextEntity and glossary Entity
"""


from termlint.core.types import MatchResultStream, TextEntityStream


class TermMatcher:

    async def match_stream(self, stream: TextEntityStream) -> MatchResultStream:
        ...
