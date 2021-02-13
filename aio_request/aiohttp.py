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

from .base import ClosableResponse, EmptyResponse, Request
from .context import set_context
from .deadline import Deadline
from .priority import Priority
from .request_sender import RequestSender
from .utils import get_headers_to_enrich

logger = logging.getLogger(__package__)


class AioHttpRequestSender(RequestSender):
    __slots__ = (
        "_client_session",
        "_service_name",
        "_network_errors_code",
        "_enrich_request_headers",
        "_buffer_payload",
        "_low_timeout_threshold",
        "_add_request_headers",
    )

    def __init__(
        self,
        client_session: aiohttp.ClientSession,
        *,
        service_name: Optional[str] = None,
        network_errors_code: int = 489,
        enrich_request_headers: Optional[Callable[[multidict.CIMultiDict[str]], None]] = None,
        buffer_payload: bool = True,
        low_timeout_threshold: float = 0.005,
        add_request_headers: bool = True,
    ):
        self._client_session = client_session
        self._service_name = service_name
        self._network_errors_code = network_errors_code
        self._enrich_request_headers = enrich_request_headers
        self._buffer_payload = buffer_payload
        self._low_timeout_threshold = low_timeout_threshold
        self._add_request_headers = add_request_headers

    async def send(self, request: Request, deadline: Deadline, priority: Priority) -> ClosableResponse:
        request_method = request.method
        request_url = request.url
        request_headers = (
            self._enrich_request_headers_(request.headers, deadline, priority)
            if self._add_request_headers
            else request.headers
        )
        request_body = request.body

        try:
            logger.debug("Sending request %s %s with timeout %s", request_method, request_url, deadline.timeout)
            if deadline.expired or deadline.timeout < self._low_timeout_threshold:
                raise asyncio.TimeoutError()
            response = await self._client_session.request(
                request_method,
                request_url,
                headers=request_headers,
                data=request_body,
                timeout=deadline.timeout,
            )
            if self._buffer_payload:
                await response.read()  # force response to buffer its body
            return _AioHttpResponse(response)
        except aiohttp.ClientError:
            logger.warning("Request %s %s has failed", request_method, request_url, exc_info=True)
            return EmptyResponse(status=self._network_errors_code)
        except asyncio.TimeoutError:
            logger.warning("Request %s %s has timed out", request_method, request_url)
            return EmptyResponse(status=408)

    def _enrich_request_headers_(
        self, headers: Optional[multidict.CIMultiDictProxy[str]], deadline: Deadline, priority: Priority
    ) -> multidict.CIMultiDict[str]:
        enriched_headers = get_headers_to_enrich(headers)
        if self._service_name is not None:
            enriched_headers.add("X-Service-Name", self._service_name)
        enriched_headers.add("X-Request-Deadline-At", str(deadline))
        enriched_headers.add("X-Request-Priority", str(priority))
        if self._enrich_request_headers is not None:
            self._enrich_request_headers(enriched_headers)
        return enriched_headers


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
        deadline = Deadline.try_parse(request.headers.get("X-Request-Deadline-At")) or Deadline.from_timeout(
            default_timeout
        )
        priority = Priority.try_parse(request.headers.get("X-Request-Priority")) or default_priority

        if deadline.expired or deadline.timeout <= low_timeout_threshold:
            return aiohttp.web_response.Response(status=408)

        with set_context(deadline=deadline, priority=priority):
            try:
                async with async_timeout.timeout(timeout=deadline.timeout):
                    return await handler(request)
            except asyncio.TimeoutError:
                return aiohttp.web_response.Response(status=408)

    return middleware
