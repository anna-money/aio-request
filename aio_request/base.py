import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Union, Any, Callable

from multidict import CIMultiDictProxy
from yarl import URL

from .utils import EMPTY_HEADERS


@dataclass(frozen=True)
class Request:
    __slots__ = ("method", "url", "headers", "body")

    method: str
    url: Union[str, URL]
    headers: Optional[CIMultiDictProxy[str]]
    body: Optional[bytes]


class Response(ABC):
    __slots__ = ()

    @property
    @abstractmethod
    def status(self) -> int:
        ...

    @property
    @abstractmethod
    def headers(self) -> CIMultiDictProxy[str]:
        ...

    @abstractmethod
    async def json(
        self,
        *,
        encoding: Optional[str] = None,
        loads: Callable[[str], Any] = json.loads,
        content_type: Optional[str] = "application/json",
    ) -> Any:
        ...

    @abstractmethod
    async def read(self) -> bytes:
        ...

    @abstractmethod
    async def text(self, encoding: Optional[str] = None) -> str:
        ...


class ClosableResponse(Response):
    __slots__ = ()

    @abstractmethod
    async def close(self) -> None:
        ...


class StaticResponse(ClosableResponse):
    __slots__ = ("_status", "_headers")

    def __init__(self, *, status: int, headers: Optional[CIMultiDictProxy[str]] = None):
        self._headers = headers or EMPTY_HEADERS
        self._status = status

    @property
    def status(self) -> int:
        return self._status

    @property
    def headers(self) -> CIMultiDictProxy[str]:
        return self._headers

    async def json(
        self,
        *,
        encoding: Optional[str] = None,
        loads: Optional[Callable[[str], Any]] = None,
        content_type: Optional[str] = "application/json",
    ) -> Any:
        return None

    async def read(self) -> bytes:
        return bytes()

    async def text(self, encoding: Optional[str] = None) -> str:
        return ""

    async def close(self) -> None:
        pass
