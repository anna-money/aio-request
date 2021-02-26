import contextlib
from typing import Any, Collection, Dict, Optional, Protocol

import multidict
import yarl

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


def substitute_path_parameters(url: yarl.URL, build_parameters: Optional[Dict[str, Any]] = None) -> yarl.URL:
    if not build_parameters:
        return url

    path = url.path
    for name, value in build_parameters.items():
        path = path.replace(f"{{{name}}}", str(value))

    build_parameters = dict(
        scheme=url.scheme,
        authority=url.authority,
        user=url.user,
        password=url.password,
        host=url.host,
        port=url.port,
        path=path,
        query=url.query,
        fragment=url.fragment,
    )

    return yarl.URL.build(**{k: v for k, v in build_parameters.items() if v is not None})
