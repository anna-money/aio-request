import asyncio
import json
from typing import Any, Callable, Optional, Union

import aiohttp
import multidict
import yarl

from .base import ClosableResponse, EmptyResponse, Request
from .deadline import Deadline
from .log import logger
from .priority import Priority
from .request_sender import RequestSender
from .utils import get_headers_to_enrich


class AioHttpRequestSender(RequestSender):
    __slots__ = (
        "_client_session",
        "_base_url",
        "_network_errors_code",
        "_enrich_request_headers",
        "_buffer_payload",
    )

    def __init__(
        self,
        client_session: aiohttp.ClientSession,
        base_url: Union[str, yarl.URL],
        *,
        network_errors_code: int = 489,
        enrich_request_headers: Optional[Callable[[multidict.CIMultiDict[str]], None]] = None,
        buffer_payload: bool = True,
    ):
        self._client_session = client_session
        self._base_url = base_url if isinstance(base_url, yarl.URL) else yarl.URL(base_url)
        self._network_errors_code = network_errors_code
        self._enrich_request_headers = enrich_request_headers
        self._buffer_payload = buffer_payload

    async def send(self, request: Request, deadline: Deadline, priority: Priority) -> ClosableResponse:
        request_method = request.method
        request_url = self._build_url(request.url)
        request_headers = self._enrich_request_headers_(request.headers, deadline, priority)
        request_body = request.body

        try:
            logger.debug("Sending request %s %s with timeout %s", request_method, request_url, deadline.timeout)
            if deadline.expired:
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
            logger.warn("Request %s %s has failed", request_method, request_url, exc_info=True)
            return EmptyResponse(status=self._network_errors_code)
        except asyncio.TimeoutError:
            logger.warn("Request %s %s has timed out", request_method, request_url)
            return EmptyResponse(status=408)

    def _enrich_request_headers_(
        self, headers: Optional[multidict.CIMultiDictProxy[str]], deadline: Deadline, priority: Priority
    ) -> multidict.CIMultiDict[str]:
        enriched_headers = get_headers_to_enrich(headers)
        enriched_headers.add("X-Request-Deadline-At", str(deadline))
        enriched_headers.add("X-Request-Priority", str(priority))
        if self._enrich_request_headers is not None:
            self._enrich_request_headers(enriched_headers)
        return enriched_headers

    def _build_url(self, url_or_str: Union[str, yarl.URL]) -> yarl.URL:
        url = url_or_str if isinstance(url_or_str, yarl.URL) else yarl.URL(url_or_str)
        return url if url.is_absolute() else self._base_url.join(url)


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
