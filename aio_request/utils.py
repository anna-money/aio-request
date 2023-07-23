import abc
import asyncio
import contextlib
from typing import Callable, Collection, Optional, TypeVar


class Closable(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def close(self) -> None:
        ...


TClosable = TypeVar("TClosable", bound=Closable)


async def close_single(item: Closable) -> None:
    with contextlib.suppress(Exception):
        await item.close()


T = TypeVar("T")


async def close_futures(items: Collection[asyncio.Future[T]], as_close: Callable[[T], TClosable]) -> None:
    for item in items:
        if item.cancelled():
            continue
        try:
            await close_single(as_close(await item))
        except asyncio.CancelledError:
            if not item.cancelled():
                raise


async def cancel_futures(futures: Collection[asyncio.Future]) -> None:
    for future in futures:
        if future.done():
            continue
        future.cancel()


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
