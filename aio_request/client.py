import asyncio
import contextlib
import time
from typing import AsyncContextManager, AsyncIterator, Callable, Optional, Union

import yarl

from .base import Method, Request, Response
from .context import get_context
from .deadline import Deadline
from .delays_provider import linear_delays
from .metrics import ClientMetricsCollector, NoMetricsCollector
from .priority import Priority
from .request_sender import RequestSender
from .response_classifier import DefaultResponseClassifier, ResponseClassifier
from .strategy import MethodBasedStrategy, RequestStrategiesFactory, RequestStrategy


class Client:
    __slots__ = (
        "_request_strategy",
        "_request_enricher",
        "_default_priority",
        "_default_timeout",
        "_metrics_collector",
    )

    def __init__(
        self,
        request_strategy: RequestStrategy,
        *,
        default_timeout: float,
        default_priority: Priority,
        request_enricher: Optional[Callable[[Request], Request]],
        metrics_collector: ClientMetricsCollector,
    ):
        self._default_priority = default_priority
        self._default_timeout = default_timeout
        self._request_enricher = request_enricher
        self._request_strategy = request_strategy
        self._metrics_collector = metrics_collector

    def request(
        self, request: Request, *, deadline: Optional[Deadline] = None, priority: Optional[Priority] = None
    ) -> AsyncContextManager[Response]:
        return self._request(request, deadline=deadline, priority=priority)

    @contextlib.asynccontextmanager
    async def _request(
        self, request: Request, *, deadline: Optional[Deadline] = None, priority: Optional[Priority] = None
    ) -> AsyncIterator[Response]:
        if self._request_enricher is not None:
            request = self._request_enricher(request)
        context = get_context()
        response_ctx = self._request_strategy.request(
            request,
            deadline or context.deadline or Deadline.from_timeout(self._default_timeout),
            self.normalize_priority(priority or self._default_priority, context.priority),
        )
        started_at = time.perf_counter()
        has_cancelled_during_request_sending = True
        try:
            async with response_ctx as response:
                elapsed = max(0.0, time.perf_counter() - started_at)
                self._metrics_collector.collect(request, response, elapsed)
                try:
                    yield response
                except asyncio.CancelledError:
                    has_cancelled_during_request_sending = False
                    raise
        except asyncio.CancelledError:
            if has_cancelled_during_request_sending:
                elapsed = max(0.0, time.perf_counter() - started_at)
                self._metrics_collector.collect(request, None, elapsed)
            raise

    @staticmethod
    def normalize_priority(priority: "Priority", context_priority: Optional["Priority"]) -> "Priority":
        if context_priority is None:
            return priority

        if priority == Priority.LOW and context_priority == Priority.HIGH:
            return Priority.NORMAL

        if priority == Priority.HIGH and context_priority == Priority.LOW:
            return Priority.NORMAL

        return priority


def setup(
    *,
    request_sender: RequestSender,
    service_url: Union[str, yarl.URL],
    service_name: str = "unknown",
    safe_method_attempts_count: int = 3,
    unsafe_method_attempts_count: int = 3,
    safe_method_delays_provider: Callable[[int], float] = linear_delays(delay_multiplier=0.1),
    unsafe_method_delays_provider: Callable[[int], float] = linear_delays(delay_multiplier=0.05),
    response_classifier: Optional[ResponseClassifier] = None,
    default_timeout: float = 20.0,
    default_priority: Priority = Priority.NORMAL,
    low_timeout_threshold: float = 0.005,
    emit_system_headers: bool = True,
    request_enricher: Optional[Callable[[Request], Request]] = None,
    metrics_collector: Optional[Callable[[str], ClientMetricsCollector]] = None,
) -> Client:
    factory = RequestStrategiesFactory(
        request_sender=request_sender,
        service_url=service_url,
        response_classifier=response_classifier or DefaultResponseClassifier(),
        low_timeout_threshold=low_timeout_threshold,
        emit_system_headers=emit_system_headers,
    )
    request_strategy = MethodBasedStrategy(
        {
            Method.GET: factory.parallel(
                attempts_count=safe_method_attempts_count, delays_provider=safe_method_delays_provider
            ),
            Method.POST: factory.sequential(
                attempts_count=unsafe_method_attempts_count, delays_provider=unsafe_method_delays_provider
            ),
            Method.PUT: factory.sequential(
                attempts_count=unsafe_method_attempts_count, delays_provider=unsafe_method_delays_provider
            ),
            Method.DELETE: factory.sequential(
                attempts_count=unsafe_method_attempts_count, delays_provider=unsafe_method_delays_provider
            ),
        }
    )
    return Client(
        request_strategy,
        default_timeout=default_timeout,
        default_priority=default_priority,
        request_enricher=request_enricher,
        metrics_collector=(metrics_collector or NoMetricsCollector)(service_name),
    )
