import abc
import asyncio
import time
from typing import Awaitable, Callable, List

import yarl

from .base import ClosableResponse, EmptyResponse, Header, Request
from .deadline import Deadline
from .metrics import MetricsProvider
from .priority import Priority
from .tracing import SpanKind, Tracer
from .transport import Transport

RequestHandler = Callable[[yarl.URL, Request, Deadline, Priority], Awaitable[ClosableResponse]]


class RequestModule(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def execute(
        self,
        next: RequestHandler,
        *,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ClosableResponse:
        ...


class LowTimeoutRequestModule(RequestModule):
    __slots__ = ("_low_timeout_threshold",)

    def __init__(self, low_timeout_threshold: float):
        self._low_timeout_threshold = low_timeout_threshold

    async def execute(
        self,
        next: RequestHandler,
        *,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ClosableResponse:
        if deadline.expired or deadline.timeout < self._low_timeout_threshold:
            return EmptyResponse(status=408)

        return await next(endpoint, request, deadline, priority)


class RequestSendingModule(RequestModule):
    __slots__ = ("_transport", "_emit_system_headers")

    def __init__(self, transport: Transport, *, emit_system_headers: bool):
        self._emit_system_headers = emit_system_headers
        self._transport = transport

    async def execute(
        self,
        _: RequestHandler,
        *,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ClosableResponse:
        if self._emit_system_headers:
            request = request.update_headers(
                {
                    Header.X_REQUEST_DEADLINE_AT: str(deadline),  # for backward compatibility
                    Header.X_REQUEST_PRIORITY: str(priority),
                    Header.X_REQUEST_TIMEOUT: str(deadline.timeout),
                }
            )

        return await self._transport.send(endpoint, request, deadline.timeout)


class MetricsModule(RequestModule):
    __slots__ = ("_metrics_provider",)

    def __init__(self, metrics_provider: MetricsProvider):
        self._metrics_provider = metrics_provider

    async def execute(
        self,
        next: RequestHandler,
        *,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ClosableResponse:
        started_at = time.perf_counter()
        try:
            response = await next(endpoint, request, deadline, priority)
            self._capture_metrics(endpoint, request, response.status, started_at)
            return response
        except asyncio.CancelledError:
            self._capture_metrics(endpoint, request, 499, started_at)
            raise

    def _capture_metrics(self, endpoint: yarl.URL, request: Request, status: int, started_at: float) -> None:
        tags = {
            "request_endpoint": endpoint.human_repr(),
            "request_method": request.method,
            "request_path": request.url.path,
            "response_status": str(status),
        }
        elapsed = max(0.0, time.perf_counter() - started_at)
        self._metrics_provider.increment_counter("aio_request_status", tags)
        self._metrics_provider.observe_value("aio_request_latency", tags, elapsed)


class TracingModule(RequestModule):
    __slots__ = ("_tracer",)

    def __init__(self, tracer: Tracer):
        self._tracer = tracer

    async def execute(
        self,
        next: RequestHandler,
        *,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ClosableResponse:
        with self._tracer.start_span("huj", SpanKind.CLIENT) as span:
            span.set_request_attrs(endpoint, request)
            response = await next(
                endpoint,
                request.update_headers(self._tracer.get_headers_to_propagate()),
                deadline,
                priority,
            )
            span.set_response_attrs(response)
            return response


def build_pipeline(modules: List[RequestModule]) -> RequestHandler:
    async def _unsupported(
        _: yarl.URL,
        __: Request,
        ___: Deadline,
        ____: Priority,
    ) -> ClosableResponse:
        raise NotImplementedError()

    def _execute_module(m: RequestModule, n: RequestHandler) -> RequestHandler:
        return lambda e, r, d, p: m.execute(n, endpoint=e, request=r, deadline=d, priority=p)

    pipeline: RequestHandler = _unsupported
    for module in reversed(modules):
        pipeline = _execute_module(module, pipeline)
    return pipeline
