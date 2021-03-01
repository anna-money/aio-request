import asyncio
import time

import yarl

from .base import ClosableResponse, EmptyResponse, Header, Request
from .deadline import Deadline
from .metrics import MetricsProvider
from .priority import Priority
from .transport import Transport


class RequestSender:
    __slots__ = ("_transport", "_metrics_provider", "_low_timeout_threshold", "_emit_system_headers")

    def __init__(
        self,
        *,
        transport: Transport,
        metrics_provider: MetricsProvider,
        emit_system_headers: bool = True,
        low_timeout_threshold: float = 0.05,
    ):
        self._transport = transport
        self._metrics_provider = metrics_provider
        self._emit_system_headers = emit_system_headers
        self._low_timeout_threshold = low_timeout_threshold

    async def send(
        self, endpoint: yarl.URL, request: Request, deadline: Deadline, priority: Priority
    ) -> ClosableResponse:
        if deadline.expired or deadline.timeout < self._low_timeout_threshold:
            return EmptyResponse(status=408)

        if self._emit_system_headers:
            request = request.update_headers(
                {
                    Header.X_REQUEST_DEADLINE_AT: str(deadline),
                    Header.X_REQUEST_PRIORITY: str(priority),
                }
            )

        started_at = time.perf_counter()
        try:
            response = await self._transport.send(endpoint, request, deadline.timeout)
            self._capture_metrics(endpoint, request, response.status, started_at)
            return response
        except asyncio.CancelledError:
            self._capture_metrics(endpoint, request, 499, started_at)
            raise

    def _capture_metrics(self, endpoint: yarl.URL, request: Request, status: int, started_at: float) -> None:
        tags = {
            "request_endpoint": endpoint.human_repr(),
            "request_method": request.method,
            "request_path": request.url.path,
            "response_status": str(status),
        }
        elapsed = max(0.0, time.perf_counter() - started_at)
        self._metrics_provider.increment_counter("aio_request_status", tags)
        self._metrics_provider.observe_value("aio_request_latency", tags, elapsed)
