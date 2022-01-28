from typing import Any, Collection, Dict

import prometheus_client

from .metrics import MetricsProvider

DEFAULT_HISTORY_BUCKETS = (
    0.005,
    0.010,
    0.025,
    0.050,
    0.075,
    0.100,
    0.125,
    0.150,
    0.175,
    0.200,
    0.300,
    0.400,
    0.500,
    1.0,
    5.0,
    10.0,
)


class PrometheusMetricsProvider(MetricsProvider):
    __slots__ = ("_metrics", "_registry", "_histogram_buckets")

    def __init__(
        self,
        registry: prometheus_client.CollectorRegistry,
        *,
        histogram_buckets: Collection[float] = DEFAULT_HISTORY_BUCKETS
    ) -> None:
        self._metrics: Dict[str, Any] = {}
        self._registry = registry
        self._histogram_buckets = histogram_buckets

    def increment_counter(self, name: str, tags: Dict[str, Any], value: float = 1) -> None:
        if name not in self._metrics:
            self._metrics[name] = prometheus_client.Counter(name, "", labelnames=tags.keys())
        self._metrics[name].labels(*[str(value) for value in tags.values()]).inc(value)

    def observe_value(self, name: str, tags: Dict[str, Any], value: float) -> None:
        if name not in self._metrics:
            self._metrics[name] = prometheus_client.Histogram(  # type: ignore
                name,
                "",
                labelnames=tags.keys(),
                buckets=self._histogram_buckets,
            )
        self._metrics[name].labels(*[str(value) for value in tags.values()]).observe(value)


PROMETHEUS_METRICS_PROVIDER = PrometheusMetricsProvider(prometheus_client.REGISTRY)
