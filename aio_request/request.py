import collections.abc
import json
from typing import Any, LiteralString

import multidict
import yarl

from .base import MAX_REDIRECTS, Header, Headers, Method, PathParameters, QueryParameters, Request

RequestEnricher = collections.abc.Callable[[Request], Request]
AsyncRequestEnricher = collections.abc.Callable[[Request], collections.abc.Awaitable[Request]]
DeprecatedAsyncRequestEnricher = collections.abc.Callable[[Request, bool], collections.abc.Awaitable[Request]]


def get(
    url: LiteralString | yarl.URL,
    *,
    headers: Headers | None = None,
    path_parameters: PathParameters | None = None,
    query_parameters: QueryParameters | None = None,
    allow_redirects: bool = True,
    max_redirects: int = MAX_REDIRECTS,
) -> Request:
    return request(
        Method.GET,
        url,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        headers=headers,
        allow_redirects=allow_redirects,
        max_redirects=max_redirects,
    )


def post(
    url: LiteralString | yarl.URL,
    body: bytes | None = None,
    *,
    headers: Headers | None = None,
    path_parameters: PathParameters | None = None,
    query_parameters: QueryParameters | None = None,
    allow_redirects: bool = True,
    max_redirects: int = MAX_REDIRECTS,
) -> Request:
    return request(
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
    url: LiteralString | yarl.URL,
    body: bytes | None = None,
    *,
    headers: Headers | None = None,
    path_parameters: PathParameters | None = None,
    query_parameters: QueryParameters | None = None,
    allow_redirects: bool = True,
    max_redirects: int = MAX_REDIRECTS,
) -> Request:
    return request(
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
    url: LiteralString | yarl.URL,
    body: bytes | None = None,
    *,
    headers: Headers | None = None,
    path_parameters: PathParameters | None = None,
    query_parameters: QueryParameters | None = None,
    allow_redirects: bool = True,
    max_redirects: int = MAX_REDIRECTS,
) -> Request:
    return request(
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
    url: LiteralString | yarl.URL,
    *,
    headers: Headers | None = None,
    path_parameters: PathParameters | None = None,
    query_parameters: QueryParameters | None = None,
    allow_redirects: bool = True,
    max_redirects: int = MAX_REDIRECTS,
) -> Request:
    return request(
        Method.DELETE,
        url,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        headers=headers,
        allow_redirects=allow_redirects,
        max_redirects=max_redirects,
    )


def post_json(
    url: LiteralString | yarl.URL,
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
    return request_json(
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
    url: LiteralString | yarl.URL,
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
    return request_json(
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
    url: LiteralString | yarl.URL,
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
    return request_json(
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


def request_json(
    method: str,
    url: LiteralString | yarl.URL,
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

    return request(
        method=method,
        url=url,
        headers=multidict.CIMultiDictProxy[str](enriched_headers),
        body=body,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        allow_redirects=allow_redirects,
        max_redirects=max_redirects,
    )


build_json_request = request_json


def request(
    method: str,
    url: LiteralString | yarl.URL,
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


build_request = request
