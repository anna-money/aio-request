import json
from typing import Any, Callable, Optional, Union

import multidict
import yarl

from .base import MAX_REDIRECTS, Header, Headers, Method, PathParameters, QueryParameters, Request


def get(
    url: Union[str, yarl.URL],
    *,
    headers: Optional[Headers] = None,
    path_parameters: Optional[PathParameters] = None,
    query_parameters: Optional[QueryParameters] = None,
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
    url: Union[str, yarl.URL],
    body: Optional[bytes] = None,
    *,
    headers: Optional[Headers] = None,
    path_parameters: Optional[PathParameters] = None,
    query_parameters: Optional[QueryParameters] = None,
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
    url: Union[str, yarl.URL],
    body: Optional[bytes] = None,
    *,
    headers: Optional[Headers] = None,
    path_parameters: Optional[PathParameters] = None,
    query_parameters: Optional[QueryParameters] = None,
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
    url: Union[str, yarl.URL],
    body: Optional[bytes] = None,
    *,
    headers: Optional[Headers] = None,
    path_parameters: Optional[PathParameters] = None,
    query_parameters: Optional[QueryParameters] = None,
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
    url: Union[str, yarl.URL],
    *,
    headers: Optional[Headers] = None,
    path_parameters: Optional[PathParameters] = None,
    query_parameters: Optional[QueryParameters] = None,
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
    url: Union[str, yarl.URL],
    data: Any,
    *,
    path_parameters: Optional[PathParameters] = None,
    query_parameters: Optional[QueryParameters] = None,
    headers: Optional[Headers] = None,
    encoding: str = "utf-8",
    dumps: Callable[[str], Any] = json.dumps,
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
    url: Union[str, yarl.URL],
    data: Any,
    *,
    path_parameters: Optional[PathParameters] = None,
    query_parameters: Optional[QueryParameters] = None,
    headers: Optional[Headers] = None,
    encoding: str = "utf-8",
    dumps: Callable[[str], Any] = json.dumps,
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
    url: Union[str, yarl.URL],
    data: Any,
    *,
    path_parameters: Optional[PathParameters] = None,
    query_parameters: Optional[QueryParameters] = None,
    headers: Optional[Headers] = None,
    encoding: str = "utf-8",
    dumps: Callable[[str], Any] = json.dumps,
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
    url: Union[str, yarl.URL],
    data: Any,
    *,
    path_parameters: Optional[PathParameters] = None,
    query_parameters: Optional[QueryParameters] = None,
    headers: Optional[Headers] = None,
    encoding: str = "utf-8",
    dumps: Callable[[Any], str] = json.dumps,
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
    url: Union[str, yarl.URL],
    *,
    path_parameters: Optional[PathParameters] = None,
    query_parameters: Optional[QueryParameters] = None,
    headers: Optional[Headers] = None,
    body: Optional[bytes] = None,
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
