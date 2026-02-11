"""
Docstring for tests.types_result

Test Result monad
"""

from src.termlint.core.types import Result


async def test_result_monad_ok():
    r1: Result[int] = Result.ok(10)
    r2: Result[int] = r1.map(lambda x: x ** 2)
    assert r2.is_ok
    assert r2.value == 100


async def test_result_monad_error():

    r1: Result[int] = Result.err(["Something went wrong"])
    r2: Result[int] = r1.map(lambda x: x ** 2)
    assert not r2.is_ok
    assert r2.errors == ["Something went wrong"]


async def test_result_monad_async_bind():

    async def degree(x: int) -> Result[int]:
        return Result.ok(x ** 2)

    r1: Result[int] = Result.ok(10)
    r2: Result[int] = await r1.bind(degree)

    assert r2.is_ok
    assert r2.value == 100
