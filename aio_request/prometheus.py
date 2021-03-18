from typing import Any

import prometheus_client

from .metrics import MetricsProvider


class PrometheusMetricsProvider(MetricsProvider):
    __slots__ = ("_metrics", "_registry")

    def __init__(self, registry: prometheus_client.CollectorRegistry) -> None:
        self._metrics: dict[str, Any] = {}
        self._registry = registry

    def increment_counter(self, name: str, tags: dict[str, Any], value: float = 1) -> None:
        if name not in self._metrics:
            self._metrics[name] = prometheus_client.Counter(name, "", labelnames=tags.keys())
        self._metrics[name].labels(*[str(value) for value in tags.values()]).inc(value)

    def observe_value(self, name: str, tags: dict[str, Any], value: float) -> None:
        if name not in self._metrics:
            self._metrics[name] = prometheus_client.Histogram(name, "", labelnames=tags.keys())
        self._metrics[name].labels(*[str(value) for value in tags.values()]).observe(value)


PROMETHEUS_METRICS_PROVIDER = PrometheusMetricsProvider(prometheus_client.REGISTRY)
