"""
Parallel processing stage for text entity extraction.
"""


import asyncio
from typing import AsyncIterator, Callable, List, Text
from src.termlint.core.models import TextEntity
from src.termlint.core.types import TextEntityStream


class ParallelStage:
    """Parallel processing stage for text entity extraction."""

    def __init__(self, extractors: List[Callable[[str], AsyncIterator[TextEntity]]]):
        self.extractors = extractors

    async def extract(self, text: str) -> TextEntityStream:
        async def parallel_extract():

            # create coroutines for each extractor
            tasks = [
                self._run_extractor(extractor, text)
                for extractor in self.extractors
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # get all results from successful extractors
            for result in results:
                if isinstance(result, list):  # List[TextEntity]
                    for entity in result:
                        yield entity

        return TextEntityStream(parallel_extract())

    async def _run_extractor(self, extractor: Callable[[str], AsyncIterator[TextEntity]], text: str):
        """Run an extractor and return a list of extracted entities."""
        iterator = extractor(text)
        return [entity async for entity in iterator]


async def example_main():
    # TODO: add to tests

    async def rule_extractor(text: str) -> AsyncIterator[TextEntity]:
        await asyncio.sleep(0.1)  # Simulate processing delay
        yield TextEntity(
            text="rule_term",
            original_text="rule_term",
            lemma="rule_term",
            span=(0, 9),
            score=0.8
        )

    async def cvalue_extractor(text: str) -> AsyncIterator[TextEntity]:
        await asyncio.sleep(0.1)  # Simulate processing delay
        yield TextEntity(
            text="cvalue_term",
            original_text="cvalue_term",
            lemma="cvalue_term",
            span=(0, 11),
            score=0.7
        )

    parallel = ParallelStage([rule_extractor, cvalue_extractor])
    stream = await parallel.extract("example text")

    entities = await stream.to_list()
    print(entities)


if __name__ == "__main__":
    asyncio.run(example_main())
