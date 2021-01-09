import asyncio
from typing import Optional, Union, Set

import aiohttp
from multidict import CIMultiDictProxy, CIMultiDict
from yarl import URL

from .deadline import Deadline
from .models import Request
from .request_sender import RequestSender, ClosableResponse
from .utils import empty_close, EMPTY_HEADERS


class AioHttpRequestSender(RequestSender):
    __slots__ = ("_base_url", "_client_session", "_network_errors_code", "_default_headers")

    def __init__(
        self,
        base_url: Union[str, URL],
        client_session: aiohttp.ClientSession,
        *,
        network_errors_code: int = 499,
        default_headers: Optional[CIMultiDictProxy[set]] = None
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
            return ClosableResponse(response.status, response.headers, await response.read(), response.close)
        except aiohttp.ClientError:
            return ClosableResponse(self._network_errors_code, EMPTY_HEADERS, bytes(), empty_close)
        except asyncio.TimeoutError:
            return ClosableResponse(408, EMPTY_HEADERS, bytes(), empty_close)

    def _enrich_headers(self, headers: Optional[CIMultiDictProxy[str]], deadline: Deadline) -> CIMultiDict[str]:
        enriched_headers = CIMultiDict[str](headers) if headers is not None else CIMultiDict[str]()
        enriched_headers.add("X-Request-Deadline", str(deadline))
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
