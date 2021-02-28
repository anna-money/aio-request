from typing import AsyncContextManager, Callable, Optional, Union

import yarl

from .base import Method, Request, Response
from .context import get_context
from .deadline import Deadline
from .delays_provider import linear_delays
from .metrics import MetricsProvider, NoopMetricsProvider
from .priority import Priority
from .request_sender import RequestSender
from .response_classifier import DefaultResponseClassifier, ResponseClassifier
from .strategy import MethodBasedStrategy, RequestStrategiesFactory, RequestStrategy
from .transport import Transport


class Client:
    __slots__ = (
        "_request_strategy",
        "_request_enricher",
        "_default_priority",
        "_default_timeout",
    )

    def __init__(
        self,
        *,
        request_strategy: RequestStrategy,
        default_timeout: float,
        default_priority: Priority,
        request_enricher: Optional[Callable[[Request], Request]],
    ):
        self._default_priority = default_priority
        self._default_timeout = default_timeout
        self._request_enricher = request_enricher
        self._request_strategy = request_strategy

    def request(
        self, request: Request, *, deadline: Optional[Deadline] = None, priority: Optional[Priority] = None
    ) -> AsyncContextManager[Response]:
        if self._request_enricher is not None:
            request = self._request_enricher(request)
        context = get_context()
        return self._request_strategy.request(
            request,
            deadline or context.deadline or Deadline.from_timeout(self._default_timeout),
            self.normalize_priority(priority or self._default_priority, context.priority),
        )

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
    transport: Transport,
    endpoint: Union[str, yarl.URL],
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
    metrics_provider: Optional[MetricsProvider] = None,
) -> Client:
    factory = RequestStrategiesFactory(
        request_sender=RequestSender(
            transport=transport,
            metrics_provider=metrics_provider or NoopMetricsProvider(),
            low_timeout_threshold=low_timeout_threshold,
            emit_system_headers=emit_system_headers,
        ),
        endpoint=endpoint,
        response_classifier=response_classifier or DefaultResponseClassifier(),
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
        request_strategy=request_strategy,
        default_timeout=default_timeout,
        default_priority=default_priority,
        request_enricher=request_enricher,
    )
