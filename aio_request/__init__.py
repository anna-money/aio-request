import collections
import re
import sys

from .base import ClosableResponse, EmptyResponse, Header, Method, Request, Response, UnexpectedContentTypeError
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
    # base.py
    "ClosableResponse",
    "EmptyResponse",
    "Header",
    "Method",
    "Request",
    "Response",
    "UnexpectedContentTypeError",
    # circuit_breaker.py
    "CircuitBreaker",
    "CircuitBreakerMetrics",
    "CircuitBreakerMetricsSnapshot",
    "CircuitState",
    "DefaultCircuitBreaker",
    "NoopCircuitBreaker",
    "RollingCircuitBreakerMetrics",
    # client.py
    "Client",
    # context.py
    "get_context",
    "set_context",
    # deadline.py
    "Deadline",
    # deadline_provider.py
    "DeadlineProvider",
    "pass_deadline_through",
    "split_deadline_between_attempts",
    # delays_provider.py
    "constant_delays",
    "linear_backoff_delays",
    "linear_delays",
    # deprecated.py
    "MetricsProvider",
    "NOOP_METRICS_PROVIDER",
    "NoopMetricsProvider",
    # endpoint_provider.py
    "EndpointProvider",
    "DelegateEndpointProvider",
    "StaticEndpointProvider",
    # pipeline.py
    "BypassModule",
    "LowTimeoutModule",
    "NextModuleFunc",
    "RequestModule",
    "TransportModule",
    "build_pipeline",
    # priority.py
    "Priority",
    # request.py
    "delete",
    "get",
    "patch",
    "patch_json",
    "post",
    "post_json",
    "put",
    "put_json",
    "request",
    "request_json",
    "RequestEnricher",
    "AsyncRequestEnricher",
    "DeprecatedAsyncRequestEnricher",
    # request_strategy.py
    "MethodBasedStrategy",
    "ParallelRequestStrategy",
    "RequestStrategy",
    "ResponseWithVerdict",
    "RetryUntilDeadlineExpiredStrategy",
    "SendRequestFunc",
    "SequentialRequestStrategy",
    "SingleAttemptRequestStrategy",
    "parallel_strategy",
    "retry_until_deadline_expired",
    "sequential_strategy",
    "single_attempt_strategy",
    # response_classifier.py
    "DefaultResponseClassifier",
    "ResponseClassifier",
    "ResponseVerdict",
    # setup.py
    "setup",
    "setup_v2",
    # transport.py
    "Transport",
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


__version__ = "0.2.1"

version = f"{__version__}, Python {sys.version}"

VersionInfo = collections.namedtuple("VersionInfo", "major minor micro release_level serial")


def _parse_version(v: str) -> VersionInfo:
    version_re = r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<micro>\d+)" r"((?P<release_level>[a-z]+)(?P<serial>\d+)?)?$"
    match = re.match(version_re, v)
    if not match:
        raise ImportError(f"Invalid package version {v}")
    try:
        major = int(match.group("major"))
        minor = int(match.group("minor"))
        micro = int(match.group("micro"))
        levels = {"rc": "candidate", "a": "alpha", "b": "beta", None: "final"}
        release_level = levels[match.group("release_level")]
        serial = int(match.group("serial")) if match.group("serial") else 0
        return VersionInfo(major, minor, micro, release_level, serial)
    except Exception as e:
        raise ImportError(f"Invalid package version {v}") from e


version_info = _parse_version(__version__)
