import collections.abc
import warnings

import yarl

from .base import ClosableResponse, Method, Request
from .circuit_breaker import CircuitBreaker
from .client import Client
from .delays_provider import linear_backoff_delays
from .deprecated import MetricsProvider
from .pipeline import BypassModule, CircuitBreakerModule, LowTimeoutModule, TransportModule, build_pipeline
from .priority import Priority
from .request_strategy import MethodBasedStrategy, RequestStrategy, sequential_strategy, single_attempt_strategy
from .response_classifier import DefaultResponseClassifier, ResponseClassifier
from .transport import Transport


def setup(
    *,
    transport: Transport,
    endpoint: str | yarl.URL,
    safe_method_strategy: RequestStrategy = sequential_strategy(
        attempts_count=3, delays_provider=linear_backoff_delays()
    ),
    unsafe_method_strategy: RequestStrategy = single_attempt_strategy(),
    response_classifier: ResponseClassifier | None = None,
    timeout: float = 20.0,
    priority: Priority = Priority.NORMAL,
    low_timeout_threshold: float = 0.005,
    emit_system_headers: bool = True,
    request_enricher: collections.abc.Callable[[Request], Request] | None = None,
    circuit_breaker: CircuitBreaker[yarl.URL, ClosableResponse] | None = None,
) -> Client:
    async def _enrich_request(request: Request, _: bool) -> Request:
        return request_enricher(request) if request_enricher is not None else request

    return setup_v2(
        transport=transport,
        endpoint=endpoint,
        safe_method_strategy=safe_method_strategy,
        unsafe_method_strategy=unsafe_method_strategy,
        response_classifier=response_classifier,
        timeout=timeout,
        priority=priority,
        low_timeout_threshold=low_timeout_threshold,
        emit_system_headers=emit_system_headers,
        request_enricher=_enrich_request,
        circuit_breaker=circuit_breaker,
    )


def setup_v2(
    *,
    transport: Transport,
    endpoint: str | yarl.URL,
    safe_method_strategy: RequestStrategy = sequential_strategy(
        attempts_count=3, delays_provider=linear_backoff_delays()
    ),
    unsafe_method_strategy: RequestStrategy = single_attempt_strategy(),
    response_classifier: ResponseClassifier | None = None,
    timeout: float = 20.0,
    priority: Priority = Priority.NORMAL,
    low_timeout_threshold: float = 0.005,
    emit_system_headers: bool = True,
    request_enricher: collections.abc.Callable[[Request, bool], collections.abc.Awaitable[Request]] | None = None,
    metrics_provider: MetricsProvider | None = None,
    circuit_breaker: CircuitBreaker[yarl.URL, ClosableResponse] | None = None,
) -> Client:
    if metrics_provider is not None:
        warnings.warn(
            "metrics_provider is deprecated, it will not be used, consider a migration to OpenTelemetry",
            DeprecationWarning,
        )

    request_strategy = MethodBasedStrategy(
        {
            Method.GET: safe_method_strategy,
            Method.POST: unsafe_method_strategy,
            Method.PUT: unsafe_method_strategy,
            Method.DELETE: unsafe_method_strategy,
            Method.PATCH: unsafe_method_strategy,
        }
    )
    return Client(
        endpoint=yarl.URL(endpoint) if isinstance(endpoint, str) else endpoint,
        response_classifier=response_classifier or DefaultResponseClassifier(),
        request_strategy=request_strategy,
        timeout=timeout,
        priority=priority,
        send_request=build_pipeline(
            [
                (
                    CircuitBreakerModule(
                        circuit_breaker,
                        response_classifier=(response_classifier or DefaultResponseClassifier()),
                    )
                    if circuit_breaker is not None
                    else BypassModule()
                ),
                LowTimeoutModule(low_timeout_threshold=low_timeout_threshold),
                TransportModule(
                    transport,
                    emit_system_headers=emit_system_headers,
                    request_enricher=request_enricher,
                ),
            ],
        ),
    )
