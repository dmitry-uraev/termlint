from ast import Call
from typing import AsyncIterable, AsyncIterator, Awaitable, Text, TypeVar, Generic, Callable, Union, List

from src.termlint.core.models import TextEntity


T = TypeVar('T')
U = TypeVar('U')


class Result(Generic[T]):
    """
    Result monad implementation to handle errors without exceptions
    """

    def __init__(self, value: Union[T, List[str]], is_ok: bool) -> None:
        self._value = value
        self._is_ok = is_ok

    @classmethod
    def ok(cls, value: T) -> 'Result[T]':
        return cls(value, True)

    @classmethod
    def err(cls, errors: List[str]) -> 'Result[T]':
        return cls(errors, False)

    @property
    def is_ok(self) -> bool:
        return self._is_ok

    @property
    def value(self) -> T:
        if not self._is_ok:
            raise ValueError("Attempting to access value of an error Result")
        return self._value # type: ignore

    @property
    def errors(self) -> List[str]:
        if self._is_ok:
            raise ValueError("Attempting to access errors of a successful Result")
        return self._value # type: ignore

    def map(self, f: Callable[[T], U]) -> 'Result[U]':
        return (Result.ok(f(self.value)) if self.is_ok else Result.err(self.errors))

    async def bind(self, f: Callable[[T], Awaitable['Result[U]']]) -> 'Result[U]':
        return (await f(self.value) if self.is_ok else Result.err(self.errors))


class TextEntityStream(AsyncIterator[TextEntity]):
    """Async iterator over text entities"""

    def __init__(self, source: AsyncIterator[TextEntity]) -> None:
        self._source = source
        # TODO: add self_closed: bool later for context management

    async def __anext__(self) -> TextEntity:
        return await anext(self._source)

    async def to_list(self) -> List[TextEntity]:
        return [entity async for entity in self]

    @classmethod
    def from_list(cls, entities: List[TextEntity]) -> 'TextEntityStream':
        """Create a TextEntityStream from a list of TextEntity objects"""
        async def _source():
            for entity in entities:
                yield entity
        return cls(_source())

    @classmethod
    def from_generator(cls, generator_func: Callable[[], AsyncIterator[TextEntity]]) -> 'TextEntityStream':
        """Create from an async iterable of TextEntity objects"""
        return cls(generator_func())
