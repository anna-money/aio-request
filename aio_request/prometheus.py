from typing import Any, Dict

import prometheus_client

from .metrics import MetricsProvider


class PrometheusMetricsProvider(MetricsProvider):
    __slots__ = ("_metrics",)

    def __init__(self) -> None:
        self._metrics: Dict[str, Any] = {}

    def increment_counter(self, name: str, tags: Dict[str, str], value: float = 1) -> None:
        if name not in self._metrics:
            self._metrics[name] = prometheus_client.Counter(name, "", labelnames=tags.keys())
        self._metrics[name].labels(*tags.values()).inc(value)

    def observe_value(self, name: str, tags: Dict[str, str], value: float) -> None:
        if name not in self._metrics:
            self._metrics[name] = prometheus_client.Histogram(name, "", labelnames=tags.keys())
        self._metrics[name].labels(*tags.values()).observe(value)
