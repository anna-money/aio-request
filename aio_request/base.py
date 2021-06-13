import abc
import json
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple, Union

import multidict
import yarl

from .utils import Closable

EMPTY_HEADERS = multidict.CIMultiDictProxy[str](multidict.CIMultiDict[str]())


class Method:
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class Header:
    CONTENT_TYPE = multidict.istr("Content-Type")
    X_REQUEST_DEADLINE_AT = multidict.istr("X-Request-Deadline-At")
    X_REQUEST_PRIORITY = multidict.istr("X-Request-Priority")
    X_REQUEST_TIMEOUT = multidict.istr("X-Request-Timeout")
    X_SERVICE_NAME = multidict.istr("X-Service-Name")


_MultiDict = Union[
    Mapping[Union[str, multidict.istr], str], multidict.CIMultiDictProxy[str], multidict.CIMultiDict[str]
]

PathParameters = Mapping[str, Any]
QueryParameters = Union[Mapping[str, Any], Iterable[Tuple[str, Any]], _MultiDict]
Headers = _MultiDict


class Request:
    __slots__ = (
        "method",
        "url",
        "path_parameters",
        "query_parameters",
        "headers",
        "body",
    )

    def __init__(
        self,
        *,
        method: str,
        url: yarl.URL,
        path_parameters: Optional[PathParameters] = None,
        query_parameters: Optional[QueryParameters] = None,
        headers: Optional[Headers] = None,
        body: Optional[bytes] = None,
    ):
        if url.is_absolute():
            raise RuntimeError("Request url should be relative")

        self.method = method
        self.path_parameters = path_parameters
        self.query_parameters = query_parameters
        self.url = url
        self.headers = headers
        self.body = body

    def update_headers(self, headers: Headers) -> "Request":
        updated_headers = (
            multidict.CIMultiDict[str](self.headers) if self.headers is not None else multidict.CIMultiDict[str]()
        )
        updated_headers.update(headers)
        return Request(
            method=self.method,
            url=self.url,
            path_parameters=self.path_parameters,
            query_parameters=self.query_parameters,
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


class ClosableResponse(Response, Closable):
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


def build_query_parameters(query_parameters: QueryParameters) -> Dict[str, Union[str, List[str]]]:
    parameters: Dict[str, Union[str, List[str]]] = {}
    for name, value in query_parameters.items() if isinstance(query_parameters, Mapping) else query_parameters:
        if value is None:
            continue
        if not isinstance(value, str) and isinstance(value, Iterable):
            values = [str(v) for v in value if v is not None]
            if not values:
                continue

            if name in parameters:
                existing_value = parameters[name]
                if isinstance(existing_value, str):
                    parameters[name] = [existing_value, *values]
                else:
                    parameters[name] = [*existing_value, *values]
            else:
                parameters[name] = values
        else:
            if name in parameters:
                existing_value = parameters[name]
                if isinstance(existing_value, str):
                    parameters[name] = [existing_value, str(value)]
                else:
                    parameters[name] = [*existing_value, str(value)]
            else:
                parameters[name] = str(value)
    return parameters


def substitute_path_parameters(url: yarl.URL, parameters: Optional[PathParameters] = None) -> yarl.URL:
    if not parameters:
        return url

    path = url.path
    for name, value in parameters.items():
        path = path.replace(f"{{{name}}}", str(value))

    build_parameters: Dict[str, Any] = dict(
        scheme=url.scheme,
        user=url.user,
        password=url.password,
        host=url.host,
        port=url.port,
        path=path,
        query=url.query,
        fragment=url.fragment,
    )

    return yarl.URL.build(**{k: v for k, v in build_parameters.items() if v is not None})
