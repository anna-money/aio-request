import abc
import asyncio
import time
from typing import Awaitable, Callable, List, Optional

import yarl

from .base import ClosableResponse, EmptyResponse, Header, Request
from .deadline import Deadline
from .metrics import MetricsProvider
from .priority import Priority
from .tracing import SpanKind, Tracer
from .transport import Transport

NextModuleFunc = Callable[[yarl.URL, Request, Deadline, Priority], Awaitable[ClosableResponse]]


class RequestModule(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def execute(
        self,
        next: NextModuleFunc,
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
        next: NextModuleFunc,
        *,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ClosableResponse:
        if deadline.expired or deadline.timeout < self._low_timeout_threshold:
            return EmptyResponse(status=408)

        return await next(endpoint, request, deadline, priority)


class TransportModule(RequestModule):
    __slots__ = ("_transport", "_emit_system_headers", "_request_enricher")

    def __init__(
        self,
        transport: Transport,
        *,
        emit_system_headers: bool,
        request_enricher: Optional[Callable[[Request, bool], Awaitable[Request]]],
    ):
        self._transport = transport
        self._emit_system_headers = emit_system_headers
        self._request_enricher = request_enricher

    async def execute(
        self,
        _: NextModuleFunc,
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

        request = (
            await self._request_enricher(request, self._emit_system_headers)
            if self._request_enricher is not None
            else request
        )

        return await self._transport.send(endpoint, request, deadline.timeout)


class MetricsModule(RequestModule):
    __slots__ = ("_metrics_provider",)

    def __init__(self, metrics_provider: MetricsProvider):
        self._metrics_provider = metrics_provider

    async def execute(
        self,
        next: NextModuleFunc,
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
    __slots__ = ("_tracer", "_emit_system_headers")

    def __init__(self, tracer: Tracer, *, emit_system_headers: bool):
        self._tracer = tracer
        self._emit_system_headers = emit_system_headers

    async def execute(
        self,
        next: NextModuleFunc,
        *,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ClosableResponse:
        span_name = str(request.url)
        with self._tracer.start_span(span_name, SpanKind.CLIENT) as span:
            span.set_request_method(request.method)
            span.set_request_endpoint(endpoint)
            span.set_request_path(request.url)

            response = await next(
                endpoint,
                (request.update_headers(self._tracer.get_context_headers()) if self._emit_system_headers else request),
                deadline,
                priority,
            )

            span.set_response_status(response.status)

            return response


def build_pipeline(modules: List[RequestModule]) -> NextModuleFunc:
    async def _unsupported(
        _: yarl.URL,
        __: Request,
        ___: Deadline,
        ____: Priority,
    ) -> ClosableResponse:
        raise NotImplementedError()

    def _execute_module(m: RequestModule, n: NextModuleFunc) -> NextModuleFunc:
        return lambda e, r, d, p: m.execute(n, endpoint=e, request=r, deadline=d, priority=p)

    pipeline: NextModuleFunc = _unsupported
    for module in reversed(modules):
        pipeline = _execute_module(module, pipeline)
    return pipeline
