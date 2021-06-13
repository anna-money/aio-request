import abc
import asyncio
import contextlib
import sys
from typing import Any, Callable, Collection, Optional, TypeVar


class Closable(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def close(self) -> None:
        ...


TClosable = TypeVar("TClosable", bound=Closable)


async def close_single(item: TClosable) -> None:
    with contextlib.suppress(Exception):
        await item.close()


T = TypeVar("T")


if sys.version_info >= (3, 9, 0):

    async def close_futures(items: Collection[asyncio.Future[T]], as_close: Callable[[T], TClosable]) -> None:
        for item in items:
            if item.cancelled():
                continue
            try:
                await close_single(as_close(await item))
            except asyncio.CancelledError:
                if not item.cancelled():
                    raise

    async def cancel_futures(futures: Collection[asyncio.Future[T]]) -> None:
        for future in futures:
            if future.done():
                continue
            future.cancel()


else:

    async def _close_futures_py38(items: Collection[Any], as_close: Callable[[Any], TClosable]) -> None:
        for item in items:
            if item.cancelled():
                continue
            try:
                await close_single(as_close(await item))
            except asyncio.CancelledError:
                if not item.cancelled():
                    raise

    async def _cancel_futures_py38(futures: Collection[Any]) -> None:
        for future in futures:
            if future.done():
                continue
            future.cancel()

    close_futures = _close_futures_py38
    cancel_futures = _cancel_futures_py38


async def close(items: Collection[TClosable]) -> None:
    for item in items:
        await close_single(item)


def try_parse_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None

    try:
        return float(value)
    except ValueError:
        return None
