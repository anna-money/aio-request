import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional, Union, AsyncContextManager, AsyncIterator

from prometheus_client import Histogram, Counter

from .base import Request, Response
from .deadline import Deadline
from .strategy import RequestStrategy

__all__ = ["PrometheusAwareStrategy"]


class PrometheusAwareStrategy(RequestStrategy):
    __slots__ = ("_request_strategy", "_service_name", "_requests_latency_histogram", "_requests_counter")

    def __init__(
        self,
        request_strategy: RequestStrategy,
        service_name: str,
        requests_latency_histogram: Histogram,
        requests_counter: Counter,
    ):
        self._requests_counter = requests_counter
        self._requests_latency_histogram = requests_latency_histogram
        self._service_name = service_name
        self._request_strategy = request_strategy

    def request(
        self, request: Request, deadline: Optional[Union[float, Deadline]] = None
    ) -> AsyncContextManager[Response]:
        return self._request(request, deadline)

    @asynccontextmanager
    async def _request(
        self, request: Request, deadline: Optional[Union[float, Deadline]] = None
    ) -> AsyncIterator[Response]:
        start_time = time.perf_counter()
        has_cancelled_during_request = True
        try:
            async with self._request_strategy.request(request, deadline) as response:
                elapsed = max(time.perf_counter() - start_time, 0)
                self._requests_latency_histogram.labels(self._service_name, request.method).observe(elapsed)
                self._requests_counter.labels(self._service_name, request.method, response.status).inc()
                try:
                    yield response
                except asyncio.CancelledError:
                    has_cancelled_during_request = False
                    raise
        except asyncio.CancelledError:
            if has_cancelled_during_request:
                elapsed = max(time.perf_counter() - start_time, 0)
                self._requests_latency_histogram.labels(self._service_name, request.method).observe(elapsed)
                self._requests_counter.labels(self._service_name, request.method, 499).inc()
            raise
