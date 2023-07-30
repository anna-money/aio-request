import abc
import asyncio
import contextlib
import time
from typing import AsyncContextManager, AsyncIterator, Awaitable, Callable, Optional

import opentelemetry.metrics as otel_metrics
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
        self._meter, self._status_counter, self._latency_histogram = None, None, None

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

        started_at = time.perf_counter()

        try:
            response_ctx = (strategy or self._request_strategy).request(
                self._send,
                self._endpoint,
                request,
                deadline or context.deadline or Deadline.from_timeout(self._timeout),
                self.normalize_priority(priority or self._priority, context.priority),
            )
            async with response_ctx as response_with_verdict:
                self._capture_metrics(
                    endpoint=self._endpoint,
                    request=request,
                    status=response_with_verdict.response.status,
                    circuit_breaker=Header.X_CIRCUIT_BREAKER in response_with_verdict.response.headers,
                    started_at=started_at,
                )
                yield response_with_verdict.response
        except asyncio.CancelledError:
            self._capture_metrics(
                endpoint=self._endpoint,
                request=request,
                status=499,
                circuit_breaker=False,
                started_at=started_at,
            )
            raise

    @staticmethod
    def normalize_priority(priority: Priority, context_priority: Optional[Priority]) -> Priority:
        if context_priority is None:
            return priority

        if priority == Priority.LOW and context_priority == Priority.HIGH:
            return Priority.NORMAL

        if priority == Priority.HIGH and context_priority == Priority.LOW:
            return Priority.NORMAL

        return priority

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
        started_at: float,
    ) -> None:
        if self._meter is None:
            self._meter = otel_metrics.get_meter(__package__)
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
        elapsed = max(0.0, time.perf_counter() - started_at)
        self._status_counter.add(1, tags)
        self._latency_histogram.record(elapsed, tags)
