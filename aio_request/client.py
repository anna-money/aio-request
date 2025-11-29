import asyncio
import collections.abc
import contextlib

import yarl

from .base import ClosableResponse, Header, Request, Response
from .context import get_context
from .deadline import Deadline
from .endpoint_provider import EndpointProvider
from .priority import Priority
from .request_strategy import RequestStrategy, ResponseWithVerdict
from .response_classifier import ResponseClassifier
from .utils import perf_counter, perf_counter_elapsed

try:
    import prometheus_client as prom

    latency_histogram = prom.Histogram(
        "aio_request_latency",
        "Duration of client requests.",
        labelnames=(
            "request_endpoint",
            "request_method",
            "request_path",
            "response_status",
            "circuit_breaker",
        ),
        buckets=(
            0.005,
            0.01,
            0.025,
            0.05,
            0.075,
            0.1,
            0.15,
            0.2,
            0.25,
            0.3,
            0.35,
            0.4,
            0.45,
            0.5,
            0.75,
            1.0,
            5.0,
            10.0,
            15.0,
            20.0,
        ),
    )

    def capture_metrics(
        *, endpoint: yarl.URL, request: Request, status: int, circuit_breaker: bool, elapsed: float
    ) -> None:
        label_values = (
            endpoint.human_repr(),
            request.method,
            request.url.path,
            str(status),
            str(circuit_breaker),
        )
        latency_histogram.labels(*label_values).observe(elapsed)

except ImportError:

    def capture_metrics(
        *, endpoint: yarl.URL, request: Request, status: int, circuit_breaker: bool, elapsed: float
    ) -> None:
        pass


class Client:
    __slots__ = (
        "__endpoint_provider",
        "__priority",
        "__request_strategy",
        "__response_classifier",
        "__send_request",
        "__timeout",
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
    ) -> None:
        self.__endpoint_provider = endpoint_provider
        self.__response_classifier = response_classifier
        self.__request_strategy = request_strategy
        self.__priority = priority
        self.__timeout = timeout
        self.__send_request = send_request

    @contextlib.asynccontextmanager
    async def request(
        self,
        request: Request,
        *,
        deadline: Deadline | None = None,
        priority: Priority | None = None,
        strategy: RequestStrategy | None = None,
    ) -> collections.abc.AsyncIterator[Response]:
        started_at = perf_counter()
        endpoint = await self.__endpoint_provider.get()
        try:
            response_ctx = self._request(
                endpoint=endpoint, request=request, deadline=deadline, priority=priority, strategy=strategy
            )
            async with response_ctx as response:
                capture_metrics(
                    endpoint=endpoint,
                    request=request,
                    status=response.status,
                    circuit_breaker=Header.X_CIRCUIT_BREAKER in response.headers,
                    elapsed=perf_counter_elapsed(started_at),
                )
                yield response
        except asyncio.CancelledError:
            capture_metrics(
                endpoint=endpoint,
                request=request,
                status=499,
                circuit_breaker=False,
                elapsed=perf_counter_elapsed(started_at),
            )
            raise

    @contextlib.asynccontextmanager
    async def _request(
        self,
        *,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline | None = None,
        priority: Priority | None = None,
        strategy: RequestStrategy | None = None,
    ) -> collections.abc.AsyncIterator[Response]:
        context = get_context()
        response_ctx = (strategy or self.__request_strategy).request(
            self.__send,
            endpoint,
            request,
            deadline or context.deadline or Deadline.from_timeout(self.__timeout),
            self.__normalize_priority(priority or self.__priority, context.priority),
        )
        async with response_ctx as response_with_verdict:
            yield response_with_verdict.response

    async def __send(
        self,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ResponseWithVerdict[ClosableResponse]:
        response = await self.__send_request(endpoint, request, deadline, priority)
        return ResponseWithVerdict(response, self.__response_classifier.classify(response))

    @staticmethod
    def __normalize_priority(priority: Priority, context_priority: Priority | None) -> Priority:
        if context_priority is None:
            return priority

        if priority == Priority.LOW and context_priority == Priority.HIGH:
            return Priority.NORMAL

        if priority == Priority.HIGH and context_priority == Priority.LOW:
            return Priority.NORMAL

        return priority
