import json
from typing import Any, Callable, Optional, Union

import multidict
import yarl

from .base import Header, Headers, Method, PathParameters, QueryParameters, Request


def get(
    url: Union[str, yarl.URL],
    *,
    headers: Optional[Headers] = None,
    path_parameters: Optional[PathParameters] = None,
    query_parameters: Optional[QueryParameters] = None,
) -> Request:
    return build_request(
        Method.GET, url, path_parameters=path_parameters, query_parameters=query_parameters, headers=headers
    )


def post(
    url: Union[str, yarl.URL],
    body: Optional[bytes] = None,
    *,
    headers: Optional[Headers] = None,
    path_parameters: Optional[PathParameters] = None,
    query_parameters: Optional[QueryParameters] = None,
) -> Request:
    return build_request(
        Method.POST, url, path_parameters=path_parameters, query_parameters=query_parameters, headers=headers, body=body
    )


def put(
    url: Union[str, yarl.URL],
    body: Optional[bytes] = None,
    *,
    headers: Optional[Headers] = None,
    path_parameters: Optional[PathParameters] = None,
    query_parameters: Optional[QueryParameters] = None,
) -> Request:
    return build_request(
        Method.PUT, url, path_parameters=path_parameters, query_parameters=query_parameters, headers=headers, body=body
    )


def delete(
    url: Union[str, yarl.URL],
    *,
    headers: Optional[Headers] = None,
    path_parameters: Optional[PathParameters] = None,
    query_parameters: Optional[QueryParameters] = None,
) -> Request:
    return build_request(
        Method.DELETE,
        url,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        headers=headers,
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
    )


def build_request(
    method: str,
    url: Union[str, yarl.URL],
    *,
    path_parameters: Optional[PathParameters] = None,
    query_parameters: Optional[QueryParameters] = None,
    headers: Optional[Headers] = None,
    body: Optional[bytes] = None,
) -> Request:
    return Request(
        method=method,
        url=yarl.URL(url) if isinstance(url, str) else url,
        headers=headers,
        body=body,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
    )
