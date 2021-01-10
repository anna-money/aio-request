from typing import Union, Optional

from multidict import CIMultiDictProxy
from yarl import URL

from .models import Request


def get(url: Union[str, URL], *, headers: Optional[CIMultiDictProxy[str]] = None) -> Request:
    return Request("GET", url, headers, None)


def post(url: Union[str, URL], body: bytes, *, headers: Optional[CIMultiDictProxy[str]] = None) -> Request:
    return Request("GET", url, headers, body)
