"""
Core types and utilities for termlint
"""

from typing import (AsyncIterator, Awaitable, Callable, Generic, List, TypeVar,
                    Union)

from termlint.core.models import MatchResult, TextEntity

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
        """"Create a successful Result containing the given value"""
        return cls(value, True)

    @classmethod
    def err(cls, errors: List[str]) -> 'Result[T]':
        """Create an error Result containing the given list of error messages"""
        return cls(errors, False)

    @property
    def is_ok(self) -> bool:
        """Check if the Result is successful"""
        return self._is_ok

    @property
    def value(self) -> T:
        """Get the value of a successful Result, or raise an error if it's an error Result"""
        if not self._is_ok:
            raise ValueError("Attempting to access value of an error Result")
        return self._value # type: ignore

    @property
    def errors(self) -> List[str]:
        """
        Get the list of error messages from an error Result,
        or raise an error if it's a successful Result
        """
        if self._is_ok:
            raise ValueError("Attempting to access errors of a successful Result")
        return self._value # type: ignore

    def map(self, f: Callable[[T], U]) -> 'Result[U]':
        """
        Apply a function to the value of a successful Result,
        or propagate the error if it's an error Result
        """
        return (Result.ok(f(self.value)) if self.is_ok else Result.err(self.errors))

    async def bind(self, f: Callable[[T], Awaitable['Result[U]']]) -> 'Result[U]':
        """Apply an async function that returns a Result to the value of a successful Result"""
        return (await f(self.value) if self.is_ok else Result.err(self.errors))


class TextEntityStream(AsyncIterator[TextEntity]):
    """Async iterator over text entities"""

    def __init__(self, source: AsyncIterator[TextEntity]) -> None:
        self._source = source
        # TODO: add self_closed: bool later for context management

    async def __anext__(self) -> TextEntity:
        return await anext(self._source)

    async def to_list(self) -> Result[List[TextEntity]]:
        """Collect all TextEntity objects from the stream into a list"""
        try:
            return Result.ok([entity async for entity in self])
        except Exception as e:  #pylint: disable=broad-exception-caught
            return Result.err([f"Error collecting TextEntityStream to list: {str(e)}"])

    @classmethod
    def from_list(cls, entities: List[TextEntity]) -> 'TextEntityStream':
        """Create a TextEntityStream from a list of TextEntity objects"""
        async def _source():
            for entity in entities:
                yield entity
        return cls(_source())

    @classmethod
    def from_generator(
        cls, generator_func: Callable[[], AsyncIterator[TextEntity]]
    ) -> 'TextEntityStream':
        """Create from an async iterable of TextEntity objects"""
        return cls(generator_func())


class MatchResultStream(AsyncIterator[MatchResult]):
    """Async iterator over match results"""

    def __init__(self, source: AsyncIterator[MatchResult]) -> None:
        self._source = source

    async def __anext__(self) -> MatchResult:
        return await anext(self._source)

    async def to_list(self) -> Result[List[MatchResult]]:
        """Collect all MatchResult objects from the stream into a list"""
        try:
            return Result.ok([m async for m in self])
        except Exception as e:
            return Result.err([f"Error collecting MathResultStream to list: {str(e)}"])

    @classmethod
    def from_list(cls, matches: List[MatchResult]) -> 'MatchResultStream':
        """Create a MatchResultStream from a list of MatchResult objects"""
        async def _source():
            for m in matches:
                yield m
        return cls(_source())

    @classmethod
    def from_generator(
        cls, generator_func: Callable[[], AsyncIterator[MatchResult]]
    ) -> 'MatchResultStream':
        """Create from an async iterable of MatchResult objects"""
        return cls(generator_func())
