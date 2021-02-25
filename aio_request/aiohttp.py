import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Optional

import aiohttp
import aiohttp.web_middlewares
import aiohttp.web_request
import aiohttp.web_response
import async_timeout
import multidict

from .base import ClosableResponse, EmptyResponse, Header, Request
from .context import set_context
from .deadline import Deadline
from .priority import Priority
from .request_sender import RequestSender

logger = logging.getLogger(__package__)


class AioHttpRequestSender(RequestSender):
    __slots__ = (
        "_client_session",
        "_network_errors_code",
        "_buffer_payload",
        "_low_timeout_threshold",
    )

    def __init__(
        self,
        client_session: aiohttp.ClientSession,
        *,
        network_errors_code: int = 489,
        buffer_payload: bool = True,
        request_enricher: Optional[Callable[[Request], Request]] = None,
    ):
        self._client_session = client_session
        self._network_errors_code = network_errors_code
        self._buffer_payload = buffer_payload
        self._request_enricher = request_enricher

    async def send(self, request: Request, deadline: Deadline, priority: Priority) -> ClosableResponse:
        if self._request_enricher:
            request = self._request_enricher(request)

        try:
            logger.debug("Sending request %s %s with timeout %s", request.method, request.url, deadline.timeout)
            response = await self._client_session.request(
                request.method,
                request.url,
                headers=request.headers,
                data=request.body,
                timeout=deadline.timeout,
            )
            if self._buffer_payload:
                await response.read()  # force response to buffer its body
            return _AioHttpResponse(response)
        except aiohttp.ClientError:
            logger.warning(
                "Request %s %s has failed",
                request.method,
                request.url,
                exc_info=True,
                extra={
                    "aio_request_method": request.method,
                    "aio_request_url": request.url,
                },
            )
            return EmptyResponse(status=self._network_errors_code)
        except asyncio.TimeoutError:
            logger.warning("Request %s %s has timed out", request.method, request.url)
            return EmptyResponse(status=408)


class _AioHttpResponse(ClosableResponse):
    __slots__ = ("_response",)

    def __init__(self, response: aiohttp.ClientResponse):
        self._response = response

    async def close(self) -> None:
        self._response.close()

    @property
    def status(self) -> int:
        return self._response.status

    @property
    def headers(self) -> multidict.CIMultiDictProxy[str]:
        return self._response.headers

    async def json(
        self,
        *,
        encoding: Optional[str] = None,
        loads: Callable[[str], Any] = json.loads,
        content_type: Optional[str] = "application/json",
    ) -> Any:
        return await self._response.json(encoding=encoding, loads=loads, content_type=content_type)

    async def read(self) -> bytes:
        return await self._response.read()

    async def text(self, encoding: Optional[str] = None) -> str:
        return await self._response.text(encoding=encoding)


_HANDLER = Callable[[aiohttp.web_request.Request], Awaitable[aiohttp.web_response.StreamResponse]]
_MIDDLEWARE = Callable[[aiohttp.web_request.Request, _HANDLER], Awaitable[aiohttp.web_response.StreamResponse]]


def aiohttp_middleware_factory(
    *,
    default_timeout: float = 60,
    default_priority: Priority = Priority.NORMAL,
    low_timeout_threshold: float = 0.005,
) -> _MIDDLEWARE:
    @aiohttp.web_middlewares.middleware
    async def middleware(
        request: aiohttp.web_request.Request, handler: _HANDLER
    ) -> aiohttp.web_response.StreamResponse:
        deadline = Deadline.try_parse(request.headers.get(Header.X_REQUEST_DEADLINE_AT)) or Deadline.from_timeout(
            default_timeout
        )
        priority = Priority.try_parse(request.headers.get(Header.X_REQUEST_PRIORITY)) or default_priority

        if deadline.expired or deadline.timeout <= low_timeout_threshold:
            return aiohttp.web_response.Response(status=408)

        with set_context(deadline=deadline, priority=priority):
            try:
                async with async_timeout.timeout(timeout=deadline.timeout):
                    return await handler(request)
            except asyncio.TimeoutError:
                return aiohttp.web_response.Response(status=408)

    return middleware
