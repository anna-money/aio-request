import contextlib
from typing import Collection, Optional, Protocol

import multidict

EMPTY_HEADERS = multidict.CIMultiDictProxy[str](multidict.CIMultiDict[str]())


def get_headers_to_enrich(headers: Optional[multidict.CIMultiDictProxy[str]]) -> multidict.CIMultiDict[str]:
    return multidict.CIMultiDict[str](headers) if headers is not None else multidict.CIMultiDict[str]()


class Closable(Protocol):
    async def close(self) -> None:
        ...


async def close_many(items: Collection[Closable]) -> None:
    for item in items:
        with contextlib.suppress(Exception):
            await item.close()
