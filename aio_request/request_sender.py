import yarl

from .base import ClosableResponse, EmptyResponse, Header, Request
from .deadline import Deadline
from .priority import Priority
from .transport import Transport


class RequestSender:
    __slots__ = ("_transport", "_low_timeout_threshold", "_emit_system_headers")

    def __init__(
        self,
        transport: Transport,
        *,
        emit_system_headers: bool = True,
        low_timeout_threshold: float = 0.05,
    ):
        self._transport = transport
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
        return await self._transport.send(endpoint, request, deadline.timeout)
