import json
from typing import Union, Optional, Any, Callable

from multidict import CIMultiDictProxy
from yarl import URL

from .base import Request
from .utils import get_headers_to_enrich


def get(url: Union[str, URL], *, headers: Optional[CIMultiDictProxy[str]] = None) -> Request:
    return Request("GET", url, headers, None)


def post(url: Union[str, URL], body: bytes, *, headers: Optional[CIMultiDictProxy[str]] = None) -> Request:
    return Request("POST", url, headers, body)


def put(url: Union[str, URL], body: bytes, *, headers: Optional[CIMultiDictProxy[str]] = None) -> Request:
    return Request("PUT", url, headers, body)


def delete(url: Union[str, URL], *, headers: Optional[CIMultiDictProxy[str]] = None) -> Request:
    return Request("DELETE", url, headers, None)


def post_json(
    url: Union[str, URL],
    data: Any,
    *,
    headers: Optional[CIMultiDictProxy[str]] = None,
    encoding: str = "utf-8",
    dumps: Callable[[str], Any] = json.loads,
    content_type: str = "application/json",
) -> Request:
    return _built_json_request(
        "POST", url, data, headers=headers, encoding=encoding, dumps=dumps, content_type=content_type
    )


def put_json(
    url: Union[str, URL],
    data: Any,
    *,
    headers: Optional[CIMultiDictProxy[str]] = None,
    encoding: str = "utf-8",
    dumps: Callable[[str], Any] = json.loads,
    content_type: str = "application/json",
) -> Request:
    return _built_json_request(
        "PUT", url, data, headers=headers, encoding=encoding, dumps=dumps, content_type=content_type
    )


def _built_json_request(
    method: str,
    url: Union[str, URL],
    data: Any,
    *,
    headers: Optional[CIMultiDictProxy[str]] = None,
    encoding: str = "utf-8",
    dumps: Callable[[Any], str] = json.loads,
    content_type: str = "application/json",
) -> Request:
    enriched_headers = get_headers_to_enrich(headers)
    enriched_headers.add("Content-Type", content_type)

    body = dumps(data).encode(encoding)

    return Request(method, url, CIMultiDictProxy[str](enriched_headers), body)
