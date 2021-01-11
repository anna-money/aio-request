import asyncio
import json
from typing import Optional, Union, Callable, Any

import aiohttp
from multidict import CIMultiDictProxy, CIMultiDict
from yarl import URL

from .base import Request
from .base import StaticResponse, ClosableResponse
from .deadline import Deadline
from .request_sender import RequestSender


class AioHttpRequestSender(RequestSender):
    __slots__ = ("_base_url", "_client_session", "_network_errors_code", "_default_headers")

    def __init__(
        self,
        base_url: Union[str, URL],
        client_session: aiohttp.ClientSession,
        *,
        network_errors_code: int = 499,
        default_headers: Optional[CIMultiDictProxy[str]] = None
    ):
        self._base_url = base_url if isinstance(base_url, URL) else URL(base_url)
        self._network_errors_code = network_errors_code
        self._client_session = client_session
        self._default_headers = default_headers

    async def send(self, request: Request, deadline: Deadline) -> ClosableResponse:
        try:
            if deadline.expired:
                raise asyncio.TimeoutError()

            response = await self._client_session.request(
                request.method,
                self._build_url(request.url),
                headers=self._enrich_headers(request.headers, deadline),
                data=request.body,
                timeout=deadline.timeout,
            )
            return _AioHttpResponse(response)
        except aiohttp.ClientError:
            return StaticResponse(status=self._network_errors_code)
        except asyncio.TimeoutError:
            return StaticResponse(status=408)

    def _enrich_headers(self, headers: Optional[CIMultiDictProxy[str]], deadline: Deadline) -> CIMultiDict[str]:
        enriched_headers = CIMultiDict[str](headers) if headers is not None else CIMultiDict[str]()
        enriched_headers.add("X-Deadline-Time", str(deadline))
        if self._default_headers is not None:
            for key, value in self._default_headers.items():
                if key in enriched_headers:
                    enriched_headers.add(key, value)
                else:
                    enriched_headers[key] = value
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
        content_type: Optional[str] = "application/json"
    ) -> Any:
        return await self._response.json(encoding=encoding, loads=loads, content_type=content_type)

    async def read(self) -> bytes:
        return await self._response.read()

    async def text(self, encoding: Optional[str] = None) -> str:
        return await self._response.text(encoding=encoding)
