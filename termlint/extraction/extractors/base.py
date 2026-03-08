"""
Extractor base class and protocol definition.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, cast
from termlint.core.models import TextEntity


class BaseExtractor(ABC):
    """
    Base class for text extractors.

    Subclasses should implement the _extract method.
    """

    def __call__(self, text: str) -> 'BaseExtractor':
        self._pending_text = text
        return self

    def __aiter__(self) -> 'BaseExtractor':
        if not hasattr(self, '_pending_text'):
            raise ValueError("Call extractor(text) first!")
        return self

    async def __anext__(self) -> TextEntity:
        if not hasattr(self, '_pending_text'):
            raise StopAsyncIteration

        text = self._pending_text
        del self._pending_text

        async_gen = cast(AsyncIterator[TextEntity], self._extract(text))
        async_iter = aiter(async_gen)
        entity = await anext(async_iter)
        return entity

    @abstractmethod
    # TODO: make public
    async def _extract(self, text: str) -> AsyncIterator[TextEntity]:
        ...


# TODO: makes no sense, remove from RuleExtractor and delete after public extract
class ConfigurableExtractor(BaseExtractor):
    """
    Base class for configurable extractors.

    Subclasses can define their own configuration parameters in the constructor.
    """

    def __init__(self, **config):
        self.config = config or {}
