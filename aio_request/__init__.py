# flake8: noqa
import collections
import re
import sys
from typing import Tuple

from .base import ClosableResponse, EmptyResponse, Header, Method, Request, Response
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerMetrics,
    CircuitBreakerMetricsSnapshot,
    CircuitState,
    DefaultCircuitBreaker,
    NoopCircuitBreaker,
    RollingCircuitBreakerMetrics,
)
from .client import Client, DefaultClient
from .context import get_context, set_context
from .deadline import Deadline
from .delays_provider import constant_delays, linear_delays
from .metrics import NOOP_METRICS_PROVIDER, MetricsProvider, NoopMetricsProvider
from .pipeline import (
    BypassModule,
    LowTimeoutModule,
    MetricsModule,
    NextModuleFunc,
    RequestModule,
    TracingModule,
    TransportModule,
    build_pipeline,
)
from .priority import Priority
from .request import delete, get, patch, patch_json, post, post_json, put, put_json
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
from .tracing import NOOP_TRACER, NoopSpan, NoopTracer, Span, Tracer
from .transport import Transport

__all__: Tuple[str, ...] = (
    # base.py
    "ClosableResponse",
    "EmptyResponse",
    "Header",
    "Method",
    "Request",
    "Response",
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
    "DefaultClient",
    # context.py
    "get_context",
    "set_context",
    # deadline.py
    "Deadline",
    # delays_provider.py
    "constant_delays",
    "linear_delays",
    # metrics.py
    "NOOP_METRICS_PROVIDER",
    "MetricsProvider",
    "NoopMetricsProvider",
    # pipeline.py
    "BypassModule",
    "LowTimeoutModule",
    "MetricsModule",
    "NextModuleFunc",
    "RequestModule",
    "TracingModule",
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
    # tracing.py
    "NOOP_TRACER",
    "NoopSpan",
    "NoopTracer",
    "Span",
    "Tracer",
    # transport.py
    "Transport",
)

try:
    import aiohttp

    from .aiohttp import AioHttpDnsResolver, AioHttpTransport, aiohttp_middleware_factory, aiohttp_timeout

    __all__ += ("AioHttpDnsResolver", "AioHttpTransport", "aiohttp_middleware_factory", "aiohttp_timeout")
except ImportError:
    pass

try:
    import prometheus_client

    from .prometheus import PROMETHEUS_METRICS_PROVIDER, PrometheusMetricsProvider

    __all__ += ("PROMETHEUS_METRICS_PROVIDER", "PrometheusMetricsProvider")
except ImportError:
    pass

try:
    import opentelemetry.propagate
    import opentelemetry.semconv
    import opentelemetry.trace

    from .opentelemetry import OpenTelemetryTracer

    __all__ += ("OpenTelemetryTracer",)
except ImportError:
    pass

__version__ = "0.1.20"

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
