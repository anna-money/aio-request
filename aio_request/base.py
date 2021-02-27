import abc
import json
from typing import Any, Callable, Mapping, Optional, Union

import multidict
import yarl

from .utils import EMPTY_HEADERS, get_headers_to_enrich


class Method:
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class Header:
    CONTENT_TYPE = multidict.istr("Content-Type")
    X_REQUEST_DEADLINE_AT = multidict.istr("X-Request-Deadline-At")
    X_REQUEST_PRIORITY = multidict.istr("X-Request-Priority")


class Request:
    __slots__ = (
        "method",
        "url",
        "path_parameters",
        "headers",
        "body",
    )

    def __init__(
        self,
        method: str,
        url: yarl.URL,
        path_parameters: Optional[Mapping[str, str]] = None,
        headers: Optional[multidict.CIMultiDictProxy[str]] = None,
        body: Optional[bytes] = None,
    ):
        if url.is_absolute():
            raise RuntimeError("Request url should be relative")

        self.method = method
        self.path_parameters = path_parameters
        self.url = url
        self.headers = headers
        self.body = body

    def update_headers(
        self, headers: Union[Mapping[Union[str, multidict.istr], str], multidict.CIMultiDictProxy[str]]
    ) -> "Request":
        updated_headers = get_headers_to_enrich(self.headers)
        updated_headers.update(headers)
        return Request(
            method=self.method,
            url=self.url,
            headers=multidict.CIMultiDictProxy[str](updated_headers),
            body=self.body,
        )


class Response(abc.ABC):
    __slots__ = ()

    @property
    @abc.abstractmethod
    def status(self) -> int:
        ...

    @property
    @abc.abstractmethod
    def headers(self) -> multidict.CIMultiDictProxy[str]:
        ...

    @abc.abstractmethod
    async def json(
        self,
        *,
        encoding: Optional[str] = None,
        loads: Callable[[str], Any] = json.loads,
        content_type: Optional[str] = "application/json",
    ) -> Any:
        ...

    @abc.abstractmethod
    async def read(self) -> bytes:
        ...

    @abc.abstractmethod
    async def text(self, encoding: Optional[str] = None) -> str:
        ...

    def is_informational(self) -> bool:
        return 100 <= self.status < 200

    def is_successful(self) -> bool:
        return 200 <= self.status < 300

    def is_redirection(self) -> bool:
        return 300 <= self.status < 400

    def is_client_error(self) -> bool:
        return 400 <= self.status < 500

    def is_server_error(self) -> bool:
        return 500 <= self.status < 600


class ClosableResponse(Response):
    __slots__ = ()

    @abc.abstractmethod
    async def close(self) -> None:
        ...


class EmptyResponse(ClosableResponse):
    __slots__ = ("_status",)

    def __init__(self, *, status: int):
        self._status = status

    @property
    def status(self) -> int:
        return self._status

    @property
    def headers(self) -> multidict.CIMultiDictProxy[str]:
        return EMPTY_HEADERS

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
