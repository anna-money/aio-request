from dataclasses import dataclass
from typing import Optional, Union

from multidict import CIMultiDictProxy
from yarl import URL


@dataclass(frozen=True)
class Request:
    __slots__ = ("method", "url", "headers", "body")

    method: str
    url: Union[str, URL]
    headers: Optional[CIMultiDictProxy[str]]
    body: Optional[bytes]


@dataclass(frozen=True)
class Response:
    __slots__ = ("code", "headers", "body")

    code: int
    headers: CIMultiDictProxy[str]
    body: bytes
