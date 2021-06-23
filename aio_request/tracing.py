import abc
import contextlib
import enum
from typing import Union

import yarl

from .base import EMPTY_HEADERS, Headers


class Span(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def set_request_method(self, method: str) -> None:
        ...

    @abc.abstractmethod
    def set_request_endpoint(self, endpoint: yarl.URL) -> None:
        ...

    @abc.abstractmethod
    def set_request_path(self, path: Union[yarl.URL, str]) -> None:
        ...

    @abc.abstractmethod
    def set_response_status(self, status: int) -> None:
        ...


class SpanKind(str, enum.Enum):
    CLIENT = "CLIENT"
    SERVER = "SERVER"


class Tracer(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def start_span(self, name: str, kind: SpanKind) -> contextlib.AbstractContextManager[Span]:
        ...

    @abc.abstractmethod
    def get_context_headers(self) -> Headers:
        ...

    @abc.abstractmethod
    def setup_context(self, headers: Headers) -> contextlib.AbstractContextManager[None]:
        ...


class NoopSpan(Span):
    def set_request_endpoint(self, endpoint: yarl.URL) -> None:
        return

    def set_request_path(self, path: Union[yarl.URL, str]) -> None:
        return

    def set_response_status(self, status: int) -> None:
        return

    __slots__ = ()

    def set_request_method(self, method: str) -> None:
        return


class NoopTracer(Tracer):

    __slots__ = ()

    def start_span(self, name: str, kind: SpanKind) -> contextlib.AbstractContextManager[Span]:
        return contextlib.nullcontext(NoopSpan())

    def get_context_headers(self) -> Headers:
        return EMPTY_HEADERS

    def setup_context(self, headers: Headers) -> contextlib.AbstractContextManager[None]:
        return contextlib.nullcontext()


NOOP_TRACER = NoopTracer()
