from typing import Optional

import prometheus_client

from .base import Request, Response
from .metrics import Metrics

requests_counter = prometheus_client.Counter(
    name="aio_request_status_code",
    documentation="Response status codes",
    labelnames=("method", "host", "path", "status"),
)

requests_latency_histogram = prometheus_client.Histogram(
    name="aio_request_latency", documentation="Response latencies", labelnames=("method", "host", "path", "status")
)


class PrometheusMetrics(Metrics):
    __slots__ = ()

    def collect(self, request: Request, response: Optional[Response], elapsed_seconds: float) -> None:
        requests_counter.labels(
            request.method, request.url.host, request.url.path, response.status if response is not None else 499
        ).inc()
        requests_latency_histogram.labels(
            request.method, request.url.host, request.url.path, response.status if response is not None else 499
        ).observe(elapsed_seconds)
