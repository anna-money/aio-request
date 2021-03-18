import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, Optional, Union, cast

import aiohttp
import aiohttp.web
import aiohttp.web_exceptions
import aiohttp.web_middlewares
import aiohttp.web_request
import aiohttp.web_response
import async_timeout
import multidict
import yarl

from .base import ClosableResponse, EmptyResponse, Header, Request
from .context import set_context
from .deadline import Deadline
from .metrics import NOOP_METRICS_PROVIDER, MetricsProvider
from .priority import Priority
from .transport import Transport
from .utils import build_query_parameters, substitute_path_parameters, try_parse_float

logger = logging.getLogger(__package__)


class AioHttpTransport(Transport):
    __slots__ = (
        "_client_session",
        "_metrics_provider",
        "_network_errors_code",
        "_buffer_payload",
    )

    def __init__(
        self,
        client_session: aiohttp.ClientSession,
        *,
        metrics_provider: MetricsProvider = NOOP_METRICS_PROVIDER,
        network_errors_code: int = 489,
        buffer_payload: bool = True,
    ):
        self._client_session = client_session
        self._metrics_provider = metrics_provider
        self._network_errors_code = network_errors_code
        self._buffer_payload = buffer_payload

    async def send(self, endpoint: yarl.URL, request: Request, timeout: float) -> ClosableResponse:
        if not endpoint.is_absolute():
            raise RuntimeError("Base url should be absolute")

        method = request.method
        url = endpoint.join(substitute_path_parameters(request.url, request.path_parameters))
        if request.query_parameters is not None:
            url = url.update_query(build_query_parameters(request.query_parameters))
        headers = request.headers
        body = request.body

        started_at = time.perf_counter()
        try:
            logger.debug(
                "Sending request %s %s with timeout %s",
                method,
                url,
                timeout,
                extra={
                    "request_method": method,
                    "request_url": url,
                    "request_timeout": timeout,
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
            self._capture_metrics(endpoint, request, response.status, started_at)
            return _AioHttpResponse(response)
        except aiohttp.ClientError:
            logger.warning(
                "Request %s %s has failed",
                method,
                url,
                exc_info=True,
                extra={
                    "request_method": method,
                    "request_url": url,
                },
            )
            self._capture_metrics(endpoint, request, self._network_errors_code, started_at)
            return EmptyResponse(status=self._network_errors_code)
        except asyncio.CancelledError:
            self._capture_metrics(endpoint, request, 499, started_at)
            raise
        except asyncio.TimeoutError:
            logger.warning(
                "Request %s %s has timed out after %s",
                method,
                url,
                timeout,
                extra={
                    "request_method": method,
                    "request_url": url,
                    "request_timeout": timeout,
                },
            )
            self._capture_metrics(endpoint, request, 408, started_at)
            return EmptyResponse(status=408)

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


def aiohttp_timeout(*, seconds: float) -> Callable[..., Any]:
    def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, "__aio_request_timeout__", seconds)
        return func

    return wrapper


def aiohttp_middleware_factory(
    *,
    timeout: float = 20,
    priority: Priority = Priority.NORMAL,
    low_timeout_threshold: float = 0.005,
    metrics_provider: MetricsProvider = NOOP_METRICS_PROVIDER,
    client_header_name: Union[str, multidict.istr] = Header.X_SERVICE_NAME,
    cancel_on_timeout: bool = False,
) -> _MIDDLEWARE:
    def capture_metrics(request: aiohttp.web_request.Request, status: int, started_at: float) -> None:
        method = request.method
        path = request.match_info.route.resource.canonical if request.match_info.route.resource else request.path
        client = request.headers.get(client_header_name, "unknown").lower()
        tags = {
            "request_client": client,
            "request_method": method,
            "request_path": path,
            "response_status": str(status),
        }
        elapsed = max(0.0, time.perf_counter() - started_at)
        metrics_provider.increment_counter("aio_request_server_status", tags)
        metrics_provider.observe_value("aio_request_server_latency", tags, elapsed)

    @aiohttp.web_middlewares.middleware
    async def middleware(
        request: aiohttp.web_request.Request, handler: _HANDLER
    ) -> aiohttp.web_response.StreamResponse:
        deadline = _get_deadline(request) or _get_deadline_from_handler(request) or Deadline.from_timeout(timeout)
        started_at = time.perf_counter()
        try:
            response: Optional[aiohttp.web_response.StreamResponse]
            if deadline.expired or deadline.timeout <= low_timeout_threshold:
                response = aiohttp.web_response.Response(status=408)
            else:
                with set_context(deadline=deadline, priority=_get_priority(request) or priority):
                    if not cancel_on_timeout:
                        response = await handler(request)
                    else:
                        try:
                            async with async_timeout.timeout(timeout=deadline.timeout):
                                response = await handler(request)
                        except asyncio.TimeoutError:
                            response = aiohttp.web_response.Response(status=408)
            capture_metrics(request, response.status, started_at)
            return response
        except asyncio.CancelledError:
            capture_metrics(request, 499, started_at)
            raise
        except aiohttp.web_exceptions.HTTPException as e:
            capture_metrics(request, e.status, started_at)
            raise
        except Exception:
            capture_metrics(request, 500, started_at)
            raise

    return middleware


def _get_deadline(request: aiohttp.web_request.Request) -> Optional[Deadline]:
    timeout = try_parse_float(request.headers.get(Header.X_REQUEST_TIMEOUT))
    if timeout is not None:
        return Deadline.from_timeout(timeout)

    return Deadline.try_parse(request.headers.get(Header.X_REQUEST_DEADLINE_AT))


def _get_priority(request: aiohttp.web_request.Request) -> Optional[Priority]:
    return Priority.try_parse(request.headers.get(Header.X_REQUEST_PRIORITY))


def _get_deadline_from_handler(request: aiohttp.web_request.Request) -> Optional[Deadline]:
    handler = request.match_info.handler
    timeout = getattr(handler, "__aio_request_timeout__", None)
    if timeout is None and _is_subclass(handler, aiohttp.web.View):
        method_handler = getattr(handler, request.method.lower(), None)
        if method_handler is not None:
            timeout = getattr(method_handler, "__aio_request_timeout__", None)

    return Deadline.from_timeout(cast(float, timeout)) if timeout is not None else None


def _is_subclass(cls: Any, cls_info: type) -> bool:
    try:
        return issubclass(cls, cls_info)
    except TypeError:
        return False
