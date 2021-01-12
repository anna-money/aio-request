import asyncio
import json
from typing import Optional, Union, Callable, Any

import aiohttp
from multidict import CIMultiDictProxy, CIMultiDict
from yarl import URL

from .base import EmptyResponse, ClosableResponse
from .base import Request
from .deadline import Deadline
from .request_sender import RequestSender
from .utils import get_headers_to_enrich


class AioHttpRequestSender(RequestSender):
    __slots__ = (
        "_base_url",
        "_client_session",
        "_network_errors_code",
        "_enrich_request_headers",
        "_buffer_payload",
    )

    def __init__(
        self,
        base_url: Union[str, URL],
        client_session: aiohttp.ClientSession,
        *,
        network_errors_code: int = 499,
        enrich_request_headers: Optional[Callable[[CIMultiDict[str]], None]] = None,
        buffer_payload: bool = True,
    ):
        self._base_url = base_url if isinstance(base_url, URL) else URL(base_url)
        self._network_errors_code = network_errors_code
        self._client_session = client_session
        self._enrich_request_headers = enrich_request_headers
        self._buffer_payload = buffer_payload

    async def send(self, request: Request, deadline: Deadline) -> ClosableResponse:
        try:
            if deadline.expired:
                raise asyncio.TimeoutError()

            response = await self._client_session.request(
                request.method,
                self._build_url(request.url),
                headers=self._enrich_request_headers_(request.headers, deadline),
                data=request.body,
                timeout=deadline.timeout,
            )
            if self._buffer_payload:
                await response.read()  # force response to buffer its body
            return _AioHttpResponse(response)
        except aiohttp.ClientError:
            return EmptyResponse(status=self._network_errors_code)
        except asyncio.TimeoutError:
            return EmptyResponse(status=408)

    def _enrich_request_headers_(
        self, headers: Optional[CIMultiDictProxy[str]], deadline: Deadline
    ) -> CIMultiDict[str]:
        enriched_headers = get_headers_to_enrich(headers)
        enriched_headers.add("X-Deadline-Time", str(deadline))
        if self._enrich_request_headers is not None:
            self._enrich_request_headers(enriched_headers)
        return enriched_headers

    def _build_url(self, url_or_str: Union[str, URL]) -> URL:
        url = url_or_str if isinstance(url_or_str, URL) else URL(url_or_str)
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
    def headers(self) -> CIMultiDictProxy[str]:
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
