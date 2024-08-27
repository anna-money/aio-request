import abc
import asyncio
import collections.abc
import contextlib
from typing import TypeVar


class Closable(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def close(self) -> None: ...


TClosable = TypeVar("TClosable", bound=Closable)


async def close_single(item: Closable) -> None:
    with contextlib.suppress(Exception):
        await item.close()


T = TypeVar("T")


async def close_futures(
    items: collections.abc.Collection[asyncio.Future[T]], as_close: collections.abc.Callable[[T], TClosable]
) -> None:
    for item in items:
        if item.cancelled():
            continue
        try:
            await close_single(as_close(await item))
        except asyncio.CancelledError:
            if not item.cancelled():
                raise


async def cancel_futures(futures: collections.abc.Collection[asyncio.Future]) -> None:
    for future in futures:
        if future.done():
            continue
        future.cancel()


async def close(items: collections.abc.Collection[TClosable]) -> None:
    for item in items:
        await close_single(item)


def try_parse_float(value: str | None) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except ValueError:
        return None
