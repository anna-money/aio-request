import contextlib
from typing import Any, Collection, Dict, Mapping, Optional, Protocol, Union

import multidict
import yarl

EMPTY_HEADERS = multidict.CIMultiDictProxy[str](multidict.CIMultiDict[str]())


def get_headers_to_enrich(
    headers: Optional[Union[Mapping[Union[str, multidict.istr], str], multidict.CIMultiDictProxy[str]]]
) -> multidict.CIMultiDict[str]:
    return multidict.CIMultiDict[str](headers) if headers is not None else multidict.CIMultiDict[str]()


class Closable(Protocol):
    async def close(self) -> None:
        ...


async def close_many(items: Collection[Closable]) -> None:
    for item in items:
        with contextlib.suppress(Exception):
            await item.close()


def substitute_path_parameters(url: yarl.URL, parameters: Optional[Mapping[str, str]] = None) -> yarl.URL:
    if not parameters:
        return url

    path = url.path
    for name, value in parameters.items():
        path = path.replace(f"{{{name}}}", value)

    build_parameters: Dict[str, Any] = dict(
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
