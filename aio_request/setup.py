import warnings
from typing import Any

import yarl

from .base import ClosableResponse, Method
from .circuit_breaker import CircuitBreaker
from .client import Client
from .delays_provider import linear_backoff_delays
from .deprecated import MetricsProvider
from .endpoint_provider import EndpointProvider, StaticEndpointProvider
from .pipeline import BypassModule, CircuitBreakerModule, LowTimeoutModule, TransportModule, build_pipeline
from .priority import Priority
from .request import AsyncRequestEnricher, DeprecatedAsyncRequestEnricher, Request, RequestEnricher
from .request_strategy import MethodBasedStrategy, RequestStrategy, sequential_strategy, single_attempt_strategy
from .response_classifier import DefaultResponseClassifier, ResponseClassifier
from .transport import Transport

MISSING: Any = object()


def setup(
    *,
    transport: Transport,
    endpoint: str | yarl.URL = MISSING,
    endpoint_provider: EndpointProvider = MISSING,
    safe_method_strategy: RequestStrategy = sequential_strategy(
        attempts_count=3, delays_provider=linear_backoff_delays()
    ),
    unsafe_method_strategy: RequestStrategy = single_attempt_strategy(),
    response_classifier: ResponseClassifier | None = None,
    timeout: float = 20.0,
    priority: Priority = Priority.NORMAL,
    low_timeout_threshold: float = 0.005,
    emit_system_headers: bool = True,
    request_enricher: RequestEnricher | AsyncRequestEnricher | None = None,
    metrics_provider: MetricsProvider | None = None,
    circuit_breaker: CircuitBreaker[yarl.URL, ClosableResponse] | None = None,
) -> Client:
    if endpoint is MISSING and endpoint_provider is MISSING:
        raise ValueError("Either endpoint or endpoint_provider must be provided")
    if endpoint is not MISSING and endpoint_provider is not MISSING:
        raise ValueError("Only one of endpoint or endpoint_provider must be provided")

    if metrics_provider is not None:
        warnings.warn(
            "metrics_provider is deprecated, it will not be used, please use builtin prometheus support",
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
        endpoint_provider=StaticEndpointProvider(endpoint) if endpoint is not MISSING else endpoint_provider,
        response_classifier=response_classifier or DefaultResponseClassifier(),
        request_strategy=request_strategy,
        timeout=timeout,
        priority=priority,
        send_request=build_pipeline(
            [
                (
                    CircuitBreakerModule(
                        circuit_breaker,
                        response_classifier=response_classifier or DefaultResponseClassifier(),
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


def setup_v2(*, request_enricher: DeprecatedAsyncRequestEnricher | None = None, **kwargs: Any) -> Client:
    warnings.warn(
        "setup_v2 is deprecated, please use setup",
        DeprecationWarning,
    )

    async def _patched_enricher(r: Request) -> Request:
        if request_enricher is None:
            return r
        return await request_enricher(r, False)

    return setup(request_enricher=_patched_enricher, **kwargs)
