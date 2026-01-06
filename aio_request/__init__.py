import sys
from importlib.metadata import version as _get_version

from .base import (
    ClosableResponse,
    EmptyResponse,
    Header,
    Headers,
    Method,
    PathParameters,
    QueryParameters,
    Request,
    Response,
    UnexpectedContentTypeError,
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerMetrics,
    CircuitBreakerMetricsSnapshot,
    CircuitState,
    DefaultCircuitBreaker,
    NoopCircuitBreaker,
    RollingCircuitBreakerMetrics,
)
from .client import Client
from .context import get_context, set_context
from .deadline import Deadline
from .deadline_provider import DeadlineProvider, pass_deadline_through, split_deadline_between_attempts
from .delays_provider import constant_delays, linear_backoff_delays, linear_delays
from .deprecated import NOOP_METRICS_PROVIDER, MetricsProvider, NoopMetricsProvider
from .endpoint_provider import DelegateEndpointProvider, EndpointProvider, StaticEndpointProvider
from .pipeline import BypassModule, LowTimeoutModule, NextModuleFunc, RequestModule, TransportModule, build_pipeline
from .priority import Priority
from .request import (
    AsyncRequestEnricher,
    DeprecatedAsyncRequestEnricher,
    RequestEnricher,
    delete,
    get,
    patch,
    patch_json,
    post,
    post_json,
    put,
    put_json,
    request,
    request_json,
)
from .request_attempt_delays_provider import RequestAttemptDelaysProvider
from .request_response_observer import RequestResponseObserver
from .request_strategy import (
    MethodBasedStrategy,
    ParallelRequestStrategy,
    RequestStrategy,
    ResponseWithVerdict,
    RetryUntilDeadlineExpiredStrategy,
    SendRequestFunc,
    SequentialRequestStrategy,
    SingleAttemptRequestStrategy,
    parallel_strategy,
    retry_until_deadline_expired,
    sequential_strategy,
    single_attempt_strategy,
)
from .response_classifier import DefaultResponseClassifier, ResponseClassifier, ResponseVerdict
from .setup import setup, setup_v2
from .transport import Transport

__all__: tuple[str, ...] = (
    "AsyncRequestEnricher",
    "BypassModule",
    "CircuitBreaker",
    "CircuitBreakerMetrics",
    "CircuitBreakerMetricsSnapshot",
    "CircuitState",
    "Client",
    "ClosableResponse",
    "Deadline",
    "DeadlineProvider",
    "DefaultCircuitBreaker",
    "DefaultResponseClassifier",
    "DelegateEndpointProvider",
    "DeprecatedAsyncRequestEnricher",
    "EmptyResponse",
    "EndpointProvider",
    "Header",
    "Headers",
    "LowTimeoutModule",
    "Method",
    "MethodBasedStrategy",
    "MetricsProvider",
    "NOOP_METRICS_PROVIDER",
    "NextModuleFunc",
    "NoopCircuitBreaker",
    "NoopMetricsProvider",
    "ParallelRequestStrategy",
    "PathParameters",
    "Priority",
    "QueryParameters",
    "Request",
    "PercentileBasedRequestAttemptDelaysProvider",
    "RequestAttemptDelaysProvider",
    "RequestResponseObserver",
    "RequestEnricher",
    "RequestModule",
    "RequestStrategy",
    "Response",
    "ResponseClassifier",
    "ResponseVerdict",
    "ResponseWithVerdict",
    "RetryUntilDeadlineExpiredStrategy",
    "RollingCircuitBreakerMetrics",
    "SendRequestFunc",
    "SequentialRequestStrategy",
    "SingleAttemptRequestStrategy",
    "StaticEndpointProvider",
    "Transport",
    "TransportModule",
    "UnexpectedContentTypeError",
    "build_pipeline",
    "constant_delays",
    "delete",
    "get",
    "get_context",
    "linear_backoff_delays",
    "linear_delays",
    "parallel_strategy",
    "pass_deadline_through",
    "patch",
    "patch_json",
    "post",
    "post_json",
    "put",
    "put_json",
    "request",
    "request_json",
    "retry_until_deadline_expired",
    "sequential_strategy",
    "set_context",
    "setup",
    "setup_v2",
    "single_attempt_strategy",
    "split_deadline_between_attempts",
)
try:
    import aiohttp  # noqa

    from .aiohttp import AioHttpDnsResolver, AioHttpTransport, aiohttp_middleware_factory, aiohttp_timeout

    __all__ += (
        "AioHttpDnsResolver",
        "AioHttpTransport",
        "aiohttp_middleware_factory",
        "aiohttp_timeout",
    )  # type: ignore
except ImportError:
    pass

try:
    import httpx  # noqa

    from .httpx import HttpxTransport

    __all__ += ("HttpxTransport",)  # type: ignore
except ImportError:
    pass

try:
    import prometheus_client  # noqa

    # Deprecated as well as MetricsProvider, NoopMetricsProvider and NOOP_METRICS_PROVIDER.
    # For backward compatibility.
    PROMETHEUS_METRICS_PROVIDER = NOOP_METRICS_PROVIDER
    PrometheusMetricsProvider = NoopMetricsProvider

    __all__ += ("PROMETHEUS_METRICS_PROVIDER", "PrometheusMetricsProvider")  # type: ignore
except ImportError:
    pass


try:
    import tdigest  # noqa

    from .percentile_based_request_attempt_delays_provider import PercentileBasedRequestAttemptDelaysProvider

    __all__ += ("PercentileBasedRequestAttemptDelaysProvider",)  # type: ignore

except ImportError:
    pass

__version__ = _get_version("aio-request")

version = f"{__version__}, Python {sys.version}"
