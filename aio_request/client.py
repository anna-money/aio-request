import contextlib
from typing import AsyncIterator, Callable, Optional, Union

import yarl

from .base import ClosableResponse, Method, Request, Response
from .context import get_context
from .deadline import Deadline
from .delays_provider import linear_delays
from .metrics import NOOP_METRICS_PROVIDER, MetricsProvider
from .pipeline import LowTimeoutRequestModule, MetricsModule, RequestSendingModule, TracingModule, build_pipeline
from .priority import Priority
from .request_strategy import (
    MethodBasedStrategy,
    RequestStrategy,
    ResponseWithVerdict,
    sequential_strategy,
    single_attempt_strategy,
)
from .response_classifier import DefaultResponseClassifier, ResponseClassifier
from .tracing import NOOP_TRACER, Tracer
from .transport import Transport


class Client:
    __slots__ = (
        "_endpoint",
        "_transport",
        "_response_classifier",
        "_request_strategy",
        "_priority",
        "_timeout",
        "_request_enricher",
        "_pipeline",
    )

    def __init__(
        self,
        *,
        endpoint: yarl.URL,
        transport: Transport,
        response_classifier: ResponseClassifier,
        request_strategy: RequestStrategy,
        timeout: float,
        priority: Priority,
        emit_system_headers: bool,
        low_timeout_threshold: float,
        request_enricher: Optional[Callable[[Request], Request]],
        metrics_provider: MetricsProvider = NOOP_METRICS_PROVIDER,
        tracer: Tracer = NOOP_TRACER,
    ):
        self._endpoint = endpoint
        self._transport = transport
        self._response_classifier = response_classifier
        self._request_strategy = request_strategy
        self._priority = priority
        self._timeout = timeout
        self._request_enricher = request_enricher
        self._pipeline = build_pipeline(
            [
                TracingModule(tracer=tracer),
                MetricsModule(metrics_provider=metrics_provider),
                LowTimeoutRequestModule(low_timeout_threshold=low_timeout_threshold),
                RequestSendingModule(transport, emit_system_headers=emit_system_headers),
            ]
        )

    @contextlib.asynccontextmanager
    async def request(
        self,
        request: Request,
        *,
        deadline: Optional[Deadline] = None,
        priority: Optional[Priority] = None,
        strategy: Optional[RequestStrategy] = None,
    ) -> AsyncIterator[Response]:
        if self._request_enricher is not None:
            request = self._request_enricher(request)
        context = get_context()
        response_ctx = (strategy or self._request_strategy).request(
            self._send_request,
            self._endpoint,
            request,
            deadline or context.deadline or Deadline.from_timeout(self._timeout),
            self.normalize_priority(priority or self._priority, context.priority),
        )
        async with response_ctx as response:
            yield response.response

    @staticmethod
    def normalize_priority(priority: Priority, context_priority: Optional[Priority]) -> Priority:
        if context_priority is None:
            return priority

        if priority == Priority.LOW and context_priority == Priority.HIGH:
            return Priority.NORMAL

        if priority == Priority.HIGH and context_priority == Priority.LOW:
            return Priority.NORMAL

        return priority

    async def _send_request(
        self, endpoint: yarl.URL, request: Request, deadline: Deadline, priority: Priority
    ) -> ResponseWithVerdict[ClosableResponse]:
        response = await self._pipeline(endpoint, request, deadline, priority)
        return ResponseWithVerdict(response, self._response_classifier.classify(response))


def setup(
    *,
    transport: Transport,
    endpoint: Union[str, yarl.URL],
    safe_method_strategy: RequestStrategy = sequential_strategy(attempts_count=3, delays_provider=linear_delays()),
    unsafe_method_strategy: RequestStrategy = single_attempt_strategy(),
    response_classifier: Optional[ResponseClassifier] = None,
    timeout: float = 20.0,
    priority: Priority = Priority.NORMAL,
    low_timeout_threshold: float = 0.005,
    emit_system_headers: bool = True,
    request_enricher: Optional[Callable[[Request], Request]] = None,
    metrics_provider: MetricsProvider = NOOP_METRICS_PROVIDER,
    tracer: Tracer = NOOP_TRACER,
) -> Client:
    request_strategy = MethodBasedStrategy(
        {
            Method.GET: safe_method_strategy,
            Method.POST: unsafe_method_strategy,
            Method.PUT: unsafe_method_strategy,
            Method.DELETE: unsafe_method_strategy,
        }
    )
    return Client(
        endpoint=yarl.URL(endpoint) if isinstance(endpoint, str) else endpoint,
        transport=transport,
        response_classifier=response_classifier or DefaultResponseClassifier(),
        request_strategy=request_strategy,
        timeout=timeout,
        priority=priority,
        request_enricher=request_enricher,
        low_timeout_threshold=low_timeout_threshold,
        emit_system_headers=emit_system_headers,
        metrics_provider=(
            # try to acquire metrics_provider from transport
            getattr(transport, "_metrics_provider", None)
            or metrics_provider
        ),
        tracer=tracer,
    )
