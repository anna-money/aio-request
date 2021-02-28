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
import yarl

from .base import ClosableResponse, EmptyResponse, Header, Request
from .context import set_context
from .deadline import Deadline
from .priority import Priority
from .transport import Transport
from .utils import substitute_path_parameters

logger = logging.getLogger(__package__)


class AioHttpTransport(Transport):
    __slots__ = ("_client_session", "_network_errors_code", "_buffer_payload")

    def __init__(
        self,
        client_session: aiohttp.ClientSession,
        *,
        network_errors_code: int = 489,
        buffer_payload: bool = True,
    ):
        self._client_session = client_session
        self._network_errors_code = network_errors_code
        self._buffer_payload = buffer_payload

    async def send(self, endpoint: yarl.URL, request: Request, timeout: float) -> ClosableResponse:
        if not endpoint.is_absolute():
            raise RuntimeError("Base url should be absolute")

        method = request.method
        url = substitute_path_parameters(endpoint.join(request.url), request.path_parameters)
        headers = request.headers
        body = request.body

        try:
            logger.debug(
                "Sending request %s %s with timeout %s",
                method,
                url,
                timeout,
                extra={
                    "aio_request_method": method,
                    "aio_request_url": url,
                    "aio_request_timeout": timeout,
                },
            )
            response = await self._client_session.request(
                method,
                url,
                headers=headers,
                data=body,
                timeout=timeout,
            )
            if self._buffer_payload:
                await response.read()  # force response to buffer its body
            return _AioHttpResponse(response)
        except aiohttp.ClientError:
            logger.warning(
                "Request %s %s has failed",
                method,
                url,
                exc_info=True,
                extra={
                    "aio_request_method": method,
                    "aio_request_url": url,
                },
            )
            return EmptyResponse(status=self._network_errors_code)
        except asyncio.TimeoutError:
            logger.warning(
                "Request %s %s has timed out after %s",
                method,
                url,
                timeout,
                extra={
                    "aio_request_method": method,
                    "aio_request_url": url,
                    "aio_request_timeout": timeout,
                },
            )
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
    default_timeout: float = 20,
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
