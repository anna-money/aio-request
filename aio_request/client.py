import asyncio
import collections.abc
import contextlib
import time

import opentelemetry.metrics
import opentelemetry.semconv.trace
import opentelemetry.trace
import yarl

from .base import ClosableResponse, Header, Request, Response
from .context import get_context
from .deadline import Deadline
from .endpoint_provider import EndpointProvider
from .priority import Priority
from .request_strategy import RequestStrategy, ResponseWithVerdict
from .response_classifier import ResponseClassifier


class Client:
    __slots__ = (
        "__endpoint_provider",
        "__response_classifier",
        "__request_strategy",
        "__priority",
        "__timeout",
        "__send_request",
        # otel metrics
        "__meter",
        "__status_counter",
        "__latency_histogram",
        # otel tracing
        "__tracer",
    )

    def __init__(
        self,
        *,
        endpoint_provider: EndpointProvider,
        response_classifier: ResponseClassifier,
        request_strategy: RequestStrategy,
        timeout: float,
        priority: Priority,
        send_request: collections.abc.Callable[
            [yarl.URL, Request, Deadline, Priority], collections.abc.Awaitable[ClosableResponse]
        ],
    ):
        self.__endpoint_provider = endpoint_provider
        self.__response_classifier = response_classifier
        self.__request_strategy = request_strategy
        self.__priority = priority
        self.__timeout = timeout
        self.__send_request = send_request
        # otel metrics
        self.__meter, self.__status_counter, self.__latency_histogram = None, None, None
        # otel tracing
        self.__tracer = None

    def request(
        self,
        request: Request,
        *,
        deadline: Deadline | None = None,
        priority: Priority | None = None,
        strategy: RequestStrategy | None = None,
    ) -> contextlib.AbstractAsyncContextManager[Response]:
        return self._request(request, deadline=deadline, priority=priority, strategy=strategy)

    @contextlib.asynccontextmanager
    async def _request(
        self,
        request: Request,
        *,
        deadline: Deadline | None = None,
        priority: Priority | None = None,
        strategy: RequestStrategy | None = None,
    ) -> collections.abc.AsyncIterator[Response]:
        context = get_context()
        started_at = time.time_ns()
        endpoint = await self.__endpoint_provider.get()
        with self._start_span(endpoint, request, started_at) as span:
            try:
                response_ctx = (strategy or self.__request_strategy).request(
                    self._send,
                    endpoint,
                    request,
                    deadline or context.deadline or Deadline.from_timeout(self.__timeout),
                    self._normalize_priority(priority or self.__priority, context.priority),
                )
                async with response_ctx as response_with_verdict:
                    response = response_with_verdict.response

                    self._capture_metrics(
                        endpoint=endpoint,
                        request=request,
                        status=response.status,
                        circuit_breaker=Header.X_CIRCUIT_BREAKER in response.headers,
                        started_at=started_at,
                    )
                    self._attach_response_status(
                        span=span,
                        status=response.status,
                        allow_redirects=request.allow_redirects,
                    )

                    yield response
            except asyncio.CancelledError:
                self._capture_metrics(
                    endpoint=endpoint,
                    request=request,
                    status=499,
                    circuit_breaker=False,
                    started_at=started_at,
                )
                self._attach_response_status(
                    span=span,
                    status=499,
                    allow_redirects=request.allow_redirects,
                )

                raise

    async def _send(
        self,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ResponseWithVerdict[ClosableResponse]:
        response = await self.__send_request(endpoint, request, deadline, priority)
        return ResponseWithVerdict(response, self.__response_classifier.classify(response))

    def _capture_metrics(
        self,
        *,
        endpoint: yarl.URL,
        request: Request,
        status: int,
        circuit_breaker: bool,
        started_at: int,
    ) -> None:
        if self.__meter is None:
            self.__meter = opentelemetry.metrics.get_meter(__package__)  # type: ignore
        if self.__status_counter is None:
            self.__status_counter = self.__meter.create_counter("aio_request_status")
        if self.__latency_histogram is None:
            self.__latency_histogram = self.__meter.create_histogram("aio_request_latency")

        tags = {
            "request_endpoint": endpoint.human_repr(),
            "request_method": request.method,
            "request_path": request.url.path,
            "response_status": str(status),
            "circuit_breaker": int(circuit_breaker),
        }
        elapsed = max(0, time.time_ns() - started_at)
        self.__status_counter.add(1, tags)
        self.__latency_histogram.record(elapsed, tags)

    @contextlib.contextmanager
    def _start_span(
        self, endpoint: yarl.URL, request: Request, started_at: int
    ) -> collections.abc.Iterator[opentelemetry.trace.Span]:
        if self.__tracer is None:
            self.__tracer = opentelemetry.trace.get_tracer(__package__)  # type: ignore

        with self.__tracer.start_as_current_span(
            name=f"{request.method} {request.url}",
            kind=opentelemetry.trace.SpanKind.CLIENT,
            attributes={
                opentelemetry.semconv.trace.SpanAttributes.HTTP_METHOD: request.method,
                opentelemetry.semconv.trace.SpanAttributes.HTTP_ROUTE: str(request.url),
                opentelemetry.semconv.trace.SpanAttributes.HTTP_URL: str(endpoint),
            },
            start_time=started_at,
        ) as span:
            yield span

    def _attach_response_status(self, *, span: opentelemetry.trace.Span, status: int, allow_redirects: bool) -> None:
        span.set_status(opentelemetry.trace.Status(self._http_status_to_status_code(status, allow_redirects)))
        span.set_attribute(opentelemetry.semconv.trace.SpanAttributes.HTTP_STATUS_CODE, status)

    @staticmethod
    def _http_status_to_status_code(
        status: int,
        allow_redirect: bool,
    ) -> opentelemetry.trace.StatusCode:
        if status < 100:
            return opentelemetry.trace.StatusCode.ERROR
        if status <= 299:
            return opentelemetry.trace.StatusCode.UNSET
        if status <= 399 and allow_redirect:
            return opentelemetry.trace.StatusCode.UNSET
        if status == 499:
            return opentelemetry.trace.StatusCode.UNSET
        return opentelemetry.trace.StatusCode.ERROR

    @staticmethod
    def _normalize_priority(priority: Priority, context_priority: Priority | None) -> Priority:
        if context_priority is None:
            return priority

        if priority == Priority.LOW and context_priority == Priority.HIGH:
            return Priority.NORMAL

        if priority == Priority.HIGH and context_priority == Priority.LOW:
            return Priority.NORMAL

        return priority
