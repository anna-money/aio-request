import collections.abc
import json
from typing import Any

import multidict
import yarl

from .base import MAX_REDIRECTS, Header, Headers, Method, PathParameters, QueryParameters, Request

SimpleRequestEnricher = collections.abc.Callable[[Request], Request]
RequestEnricher = collections.abc.Callable[[Request, bool], collections.abc.Awaitable[Request]]


def get(
    url: str | yarl.URL,
    *,
    headers: Headers | None = None,
    path_parameters: PathParameters | None = None,
    query_parameters: QueryParameters | None = None,
    allow_redirects: bool = True,
    max_redirects: int = MAX_REDIRECTS,
) -> Request:
    return build_request(
        Method.GET,
        url,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        headers=headers,
        allow_redirects=allow_redirects,
        max_redirects=max_redirects,
    )


def post(
    url: str | yarl.URL,
    body: bytes | None = None,
    *,
    headers: Headers | None = None,
    path_parameters: PathParameters | None = None,
    query_parameters: QueryParameters | None = None,
    allow_redirects: bool = True,
    max_redirects: int = MAX_REDIRECTS,
) -> Request:
    return build_request(
        Method.POST,
        url,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        headers=headers,
        body=body,
        allow_redirects=allow_redirects,
        max_redirects=max_redirects,
    )


def put(
    url: str | yarl.URL,
    body: bytes | None = None,
    *,
    headers: Headers | None = None,
    path_parameters: PathParameters | None = None,
    query_parameters: QueryParameters | None = None,
    allow_redirects: bool = True,
    max_redirects: int = MAX_REDIRECTS,
) -> Request:
    return build_request(
        Method.PUT,
        url,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        headers=headers,
        body=body,
        allow_redirects=allow_redirects,
        max_redirects=max_redirects,
    )


def patch(
    url: str | yarl.URL,
    body: bytes | None = None,
    *,
    headers: Headers | None = None,
    path_parameters: PathParameters | None = None,
    query_parameters: QueryParameters | None = None,
    allow_redirects: bool = True,
    max_redirects: int = MAX_REDIRECTS,
) -> Request:
    return build_request(
        Method.PATCH,
        url,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        headers=headers,
        body=body,
        allow_redirects=allow_redirects,
        max_redirects=max_redirects,
    )


def delete(
    url: str | yarl.URL,
    *,
    headers: Headers | None = None,
    path_parameters: PathParameters | None = None,
    query_parameters: QueryParameters | None = None,
    allow_redirects: bool = True,
    max_redirects: int = MAX_REDIRECTS,
) -> Request:
    return build_request(
        Method.DELETE,
        url,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        headers=headers,
        allow_redirects=allow_redirects,
        max_redirects=max_redirects,
    )


def post_json(
    url: str | yarl.URL,
    data: Any,
    *,
    path_parameters: PathParameters | None = None,
    query_parameters: QueryParameters | None = None,
    headers: Headers | None = None,
    encoding: str = "utf-8",
    dumps: collections.abc.Callable[[str], Any] = json.dumps,
    content_type: str = "application/json",
    allow_redirects: bool = True,
    max_redirects: int = MAX_REDIRECTS,
) -> Request:
    return build_json_request(
        Method.POST,
        url,
        data,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        headers=headers,
        encoding=encoding,
        dumps=dumps,
        content_type=content_type,
        allow_redirects=allow_redirects,
        max_redirects=max_redirects,
    )


def put_json(
    url: str | yarl.URL,
    data: Any,
    *,
    path_parameters: PathParameters | None = None,
    query_parameters: QueryParameters | None = None,
    headers: Headers | None = None,
    encoding: str = "utf-8",
    dumps: collections.abc.Callable[[str], Any] = json.dumps,
    content_type: str = "application/json",
    allow_redirects: bool = True,
    max_redirects: int = MAX_REDIRECTS,
) -> Request:
    return build_json_request(
        Method.PUT,
        url,
        data,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        headers=headers,
        encoding=encoding,
        dumps=dumps,
        content_type=content_type,
        allow_redirects=allow_redirects,
        max_redirects=max_redirects,
    )


def patch_json(
    url: str | yarl.URL,
    data: Any,
    *,
    path_parameters: PathParameters | None = None,
    query_parameters: QueryParameters | None = None,
    headers: Headers | None = None,
    encoding: str = "utf-8",
    dumps: collections.abc.Callable[[str], Any] = json.dumps,
    content_type: str = "application/json",
    allow_redirects: bool = True,
    max_redirects: int = MAX_REDIRECTS,
) -> Request:
    return build_json_request(
        Method.PATCH,
        url,
        data,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        headers=headers,
        encoding=encoding,
        dumps=dumps,
        content_type=content_type,
        allow_redirects=allow_redirects,
        max_redirects=max_redirects,
    )


def build_json_request(
    method: str,
    url: str | yarl.URL,
    data: Any,
    *,
    path_parameters: PathParameters | None = None,
    query_parameters: QueryParameters | None = None,
    headers: Headers | None = None,
    encoding: str = "utf-8",
    dumps: collections.abc.Callable[[Any], str] = json.dumps,
    content_type: str = "application/json",
    allow_redirects: bool = True,
    max_redirects: int = MAX_REDIRECTS,
) -> Request:
    enriched_headers = multidict.CIMultiDict[str](headers) if headers is not None else multidict.CIMultiDict[str]()
    enriched_headers.add(Header.CONTENT_TYPE, content_type)

    body = dumps(data).encode(encoding)

    return build_request(
        method=method,
        url=url,
        headers=multidict.CIMultiDictProxy[str](enriched_headers),
        body=body,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        allow_redirects=allow_redirects,
        max_redirects=max_redirects,
    )


def build_request(
    method: str,
    url: str | yarl.URL,
    *,
    path_parameters: PathParameters | None = None,
    query_parameters: QueryParameters | None = None,
    headers: Headers | None = None,
    body: bytes | None = None,
    allow_redirects: bool = True,
    max_redirects: int = MAX_REDIRECTS,
) -> Request:
    return Request(
        method=method,
        url=yarl.URL(url) if isinstance(url, str) else url,
        headers=headers,
        body=body,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        allow_redirects=allow_redirects,
        max_redirects=max_redirects,
    )
