import json
from typing import Any, Callable, Dict, Optional, Union

import multidict
import yarl

from .base import Header, Method, Request
from .utils import get_headers_to_enrich


def get(
    url: Union[str, yarl.URL],
    *,
    headers: Optional[multidict.CIMultiDictProxy[str]] = None,
    path_parameters: Optional[Dict[str, Any]] = None,
) -> Request:
    return build_request(Method.GET, url, headers=headers, path_parameters=path_parameters)


def post(
    url: Union[str, yarl.URL],
    body: Optional[bytes] = None,
    *,
    headers: Optional[multidict.CIMultiDictProxy[str]] = None,
    path_parameters: Optional[Dict[str, Any]] = None,
) -> Request:
    return build_request(Method.POST, url, headers=headers, body=body, path_parameters=path_parameters)


def put(
    url: Union[str, yarl.URL],
    body: Optional[bytes] = None,
    *,
    headers: Optional[multidict.CIMultiDictProxy[str]] = None,
    path_parameters: Optional[Dict[str, Any]] = None,
) -> Request:
    return build_request(Method.PUT, url, headers=headers, body=body, path_parameters=path_parameters)


def delete(
    url: Union[str, yarl.URL],
    *,
    headers: Optional[multidict.CIMultiDictProxy[str]] = None,
    path_parameters: Optional[Dict[str, Any]] = None,
) -> Request:
    return build_request(Method.DELETE, url, headers=headers, path_parameters=path_parameters)


def post_json(
    url: Union[str, yarl.URL],
    data: Any,
    *,
    headers: Optional[multidict.CIMultiDictProxy[str]] = None,
    encoding: str = "utf-8",
    dumps: Callable[[str], Any] = json.dumps,
    content_type: str = "application/json",
) -> Request:
    return build_json_request(
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
    return build_json_request(
        Method.PUT, url, data, headers=headers, encoding=encoding, dumps=dumps, content_type=content_type
    )


def build_json_request(
    method: str,
    url: Union[str, yarl.URL],
    data: Any,
    *,
    headers: Optional[multidict.CIMultiDictProxy[str]] = None,
    path_parameters: Optional[Dict[str, Any]] = None,
    encoding: str = "utf-8",
    dumps: Callable[[Any], str] = json.dumps,
    content_type: str = "application/json",
) -> Request:
    enriched_headers = get_headers_to_enrich(headers)
    enriched_headers.add(Header.CONTENT_TYPE, content_type)

    body = dumps(data).encode(encoding)

    return build_request(
        method=method,
        url=url,
        headers=multidict.CIMultiDictProxy[str](enriched_headers),
        body=body,
        path_parameters=path_parameters,
    )


def build_request(
    method: str,
    url: Union[str, yarl.URL],
    *,
    headers: Optional[multidict.CIMultiDictProxy[str]] = None,
    body: Optional[bytes] = None,
    path_parameters: Optional[Dict[str, Any]] = None,
) -> Request:
    return Request(
        method=method,
        url=yarl.URL(url) if isinstance(url, str) else url,
        headers=headers,
        body=body,
        path_parameters=path_parameters,
    )
