from typing import Optional

import prometheus_client

from .base import Request, Response
from .metrics_collector import MetricsCollector

requests_counter = prometheus_client.Counter(
    name="aio_request_status",
    documentation="Response status",
    labelnames=("aio_request_service_name", "aio_request_method", "aio_request_path", "aio_request_status"),
)

requests_latency_histogram = prometheus_client.Histogram(
    name="aio_request_latency",
    documentation="Request latencies",
    labelnames=("aio_request_service_name", "aio_request_method", "aio_request_path", "aio_request_status"),
)


class PrometheusMetricsCollector(MetricsCollector):
    __slots__ = ()

    def collect(self, request: Request, response: Optional[Response], elapsed_seconds: float) -> None:
        labels = (
            self._service_name,
            request.method,
            request.url.path,
            response.status if response is not None else 499,
        )
        requests_counter.labels(*labels).inc()
        requests_latency_histogram.labels(*labels).observe(elapsed_seconds)
