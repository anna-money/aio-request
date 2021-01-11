from typing import Union, Optional

from multidict import CIMultiDictProxy
from yarl import URL

from .base import Request


def get(url: Union[str, URL], *, headers: Optional[CIMultiDictProxy[str]] = None) -> Request:
    return Request("GET", url, headers, None)


def post(url: Union[str, URL], body: bytes, *, headers: Optional[CIMultiDictProxy[str]] = None) -> Request:
    return Request("POST", url, headers, body)


def put(url: Union[str, URL], body: bytes, *, headers: Optional[CIMultiDictProxy[str]] = None) -> Request:
    return Request("PUT", url, headers, body)


def delete(url: Union[str, URL], body: bytes, *, headers: Optional[CIMultiDictProxy[str]] = None) -> Request:
    return Request("POST", url, headers, body)
