import abc
import contextlib
import enum

import yarl

from .base import EMPTY_HEADERS, Headers, Request, Response


class Span(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def set_request_attrs(self, endpoint: yarl.URL, request: Request) -> None:
        ...

    @abc.abstractmethod
    def set_response_attrs(self, response: Response) -> None:
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
    def get_headers_to_propagate(self) -> Headers:
        ...

    @abc.abstractmethod
    def setup_context(self, headers: Headers) -> contextlib.AbstractContextManager[None]:
        ...


class NoopSpan(Span):
    __slots__ = ()

    def set_request_attrs(self, endpoint: yarl.URL, request: Request) -> None:
        return None

    def set_response_attrs(self, response: Response) -> None:
        return None


class NoopTracer(Tracer):

    __slots__ = ()

    def start_span(self, name: str, kind: SpanKind) -> contextlib.AbstractContextManager[Span]:
        return contextlib.nullcontext(NoopSpan())

    def get_headers_to_propagate(self) -> Headers:
        return EMPTY_HEADERS

    def setup_context(self, headers: Headers) -> contextlib.AbstractContextManager[None]:
        return contextlib.nullcontext()


NOOP_TRACER = NoopTracer()
