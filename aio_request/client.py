import abc
import asyncio
import contextlib
import time
from typing import AsyncContextManager, AsyncIterator, Awaitable, Callable, Iterator, Optional

import opentelemetry.metrics
import opentelemetry.semconv.trace
import opentelemetry.trace
import yarl

from .base import ClosableResponse, Header, Request, Response
from .context import get_context
from .deadline import Deadline
from .priority import Priority
from .request_strategy import RequestStrategy, ResponseWithVerdict
from .response_classifier import ResponseClassifier


class Client(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def request(
        self,
        request: Request,
        *,
        deadline: Optional[Deadline] = None,
        priority: Optional[Priority] = None,
        strategy: Optional[RequestStrategy] = None,
    ) -> AsyncContextManager[Response]:
        ...


class DefaultClient(Client):
    __slots__ = (
        "_endpoint",
        "_response_classifier",
        "_request_strategy",
        "_priority",
        "_timeout",
        "_send_request",
        # otel metrics
        "_meter",
        "_status_counter",
        "_latency_histogram",
        # otel tracing
        "_tracer",
    )

    def __init__(
        self,
        *,
        endpoint: yarl.URL,
        response_classifier: ResponseClassifier,
        request_strategy: RequestStrategy,
        timeout: float,
        priority: Priority,
        send_request: Callable[[yarl.URL, Request, Deadline, Priority], Awaitable[ClosableResponse]],
    ):
        self._endpoint = endpoint
        self._response_classifier = response_classifier
        self._request_strategy = request_strategy
        self._priority = priority
        self._timeout = timeout
        self._send_request = send_request
        # otel metrics
        self._meter, self._status_counter, self._latency_histogram = None, None, None
        # otel tracing
        self._tracer = None

    def request(
        self,
        request: Request,
        *,
        deadline: Optional[Deadline] = None,
        priority: Optional[Priority] = None,
        strategy: Optional[RequestStrategy] = None,
    ) -> AsyncContextManager[Response]:
        return self._request(request, deadline=deadline, priority=priority, strategy=strategy)

    @contextlib.asynccontextmanager
    async def _request(
        self,
        request: Request,
        *,
        deadline: Optional[Deadline] = None,
        priority: Optional[Priority] = None,
        strategy: Optional[RequestStrategy] = None,
    ) -> AsyncIterator[Response]:
        context = get_context()
        started_at = time.time_ns()

        with self._start_span(request, started_at) as span:
            try:
                response_ctx = (strategy or self._request_strategy).request(
                    self._send,
                    self._endpoint,
                    request,
                    deadline or context.deadline or Deadline.from_timeout(self._timeout),
                    self._normalize_priority(priority or self._priority, context.priority),
                )
                async with response_ctx as response_with_verdict:
                    response = response_with_verdict.response

                    self._capture_metrics(
                        endpoint=self._endpoint,
                        request=request,
                        status=response.status,
                        circuit_breaker=Header.X_CIRCUIT_BREAKER in response.headers,
                        started_at=started_at,
                    )
                    self._attach_response_status(span, response.status)

                    yield response
            except asyncio.CancelledError:
                self._capture_metrics(
                    endpoint=self._endpoint,
                    request=request,
                    status=499,
                    circuit_breaker=False,
                    started_at=started_at,
                )
                self._attach_response_status(span, 499)

                raise

    async def _send(
        self,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ResponseWithVerdict[ClosableResponse]:
        response = await self._send_request(endpoint, request, deadline, priority)
        return ResponseWithVerdict(response, self._response_classifier.classify(response))

    def _capture_metrics(
        self,
        *,
        endpoint: yarl.URL,
        request: Request,
        status: int,
        circuit_breaker: bool,
        started_at: int,
    ) -> None:
        if self._meter is None:
            self._meter = opentelemetry.metrics.get_meter(__package__)
        if self._status_counter is None:
            self._status_counter = self._meter.create_counter("aio_request_status")
        if self._latency_histogram is None:
            self._latency_histogram = self._meter.create_histogram("aio_request_latency")

        tags = {
            "request_endpoint": endpoint.human_repr(),
            "request_method": request.method,
            "request_path": request.url.path,
            "response_status": str(status),
            "circuit_breaker": int(circuit_breaker),
        }
        elapsed = max(0, time.time_ns() - started_at)
        self._status_counter.add(1, tags)
        self._latency_histogram.record(elapsed, tags)

    @contextlib.contextmanager
    def _start_span(self, request: request, started_at: int) -> Iterator[opentelemetry.trace.Span]:  # type: ignore
        if self._tracer is None:
            self._tracer = opentelemetry.trace.get_tracer(__package__)

        with self._tracer.start_as_current_span(
            name=f"{request.method} {request.url}",
            kind=opentelemetry.trace.SpanKind.CLIENT,
            attributes={
                opentelemetry.semconv.trace.SpanAttributes.HTTP_METHOD: request.method,
                opentelemetry.semconv.trace.SpanAttributes.HTTP_ROUTE: str(request.url),
                opentelemetry.semconv.trace.SpanAttributes.HTTP_URL: str(self._endpoint),
            },
            start_time=started_at,
        ) as span:
            yield span

    def _attach_response_status(self, span: opentelemetry.trace.Span, status: int) -> None:
        span.set_status(opentelemetry.trace.Status(self._http_status_to_status_code(status)))
        span.set_attribute(opentelemetry.semconv.trace.SpanAttributes.HTTP_STATUS_CODE, status)

    @staticmethod
    def _http_status_to_status_code(
        status: int,
        allow_redirect: bool = True,
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
    def _normalize_priority(priority: Priority, context_priority: Optional[Priority]) -> Priority:
        if context_priority is None:
            return priority

        if priority == Priority.LOW and context_priority == Priority.HIGH:
            return Priority.NORMAL

        if priority == Priority.HIGH and context_priority == Priority.LOW:
            return Priority.NORMAL

        return priority
