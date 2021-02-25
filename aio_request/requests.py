import json
from typing import Any, Callable, Optional, Union

import multidict
import yarl

from .base import Header, Method, Request
from .utils import get_headers_to_enrich


def get(url: Union[str, yarl.URL], *, headers: Optional[multidict.CIMultiDictProxy[str]] = None) -> Request:
    return Request(Method.GET, url, headers, None)


def post(
    url: Union[str, yarl.URL],
    body: Optional[bytes] = None,
    *,
    headers: Optional[multidict.CIMultiDictProxy[str]] = None,
) -> Request:
    return Request(Method.POST, url, headers, body)


def put(
    url: Union[str, yarl.URL],
    body: Optional[bytes] = None,
    *,
    headers: Optional[multidict.CIMultiDictProxy[str]] = None,
) -> Request:
    return Request(Method.PUT, url, headers, body)


def delete(url: Union[str, yarl.URL], *, headers: Optional[multidict.CIMultiDictProxy[str]] = None) -> Request:
    return Request(Method.DELETE, url, headers, None)


def post_json(
    url: Union[str, yarl.URL],
    data: Any,
    *,
    headers: Optional[multidict.CIMultiDictProxy[str]] = None,
    encoding: str = "utf-8",
    dumps: Callable[[str], Any] = json.dumps,
    content_type: str = "application/json",
) -> Request:
    return _built_json_request(
        Method.POST, url, data, headers=headers, encoding=encoding, dumps=dumps, content_type=content_type
    )


def put_json(
    url: Union[str, yarl.URL],
    data: Any,
    *,
    headers: Optional[multidict.CIMultiDictProxy[str]] = None,
    encoding: str = "utf-8",
    dumps: Callable[[str], Any] = json.dumps,
    content_type: str = "application/json",
) -> Request:
    return _built_json_request(
        Method.PUT, url, data, headers=headers, encoding=encoding, dumps=dumps, content_type=content_type
    )


def _built_json_request(
    method: str,
    url: Union[str, yarl.URL],
    data: Any,
    *,
    headers: Optional[multidict.CIMultiDictProxy[str]] = None,
    encoding: str = "utf-8",
    dumps: Callable[[Any], str] = json.dumps,
    content_type: str = "application/json",
) -> Request:
    enriched_headers = get_headers_to_enrich(headers)
    enriched_headers.add(Header.CONTENT_TYPE, content_type)

    body = dumps(data).encode(encoding)

    return Request(method, url, multidict.CIMultiDictProxy[str](enriched_headers), body)
