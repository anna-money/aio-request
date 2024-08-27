import asyncio
import collections.abc
import contextlib
import json
import logging
import sys
import time
import warnings
from typing import Any

import aiohttp
import aiohttp.abc
import aiohttp.web
import aiohttp.web_exceptions
import aiohttp.web_middlewares
import aiohttp.web_request
import aiohttp.web_response
import multidict
import opentelemetry.metrics
import yarl

from .deprecated import MetricsProvider

if sys.version_info < (3, 11, 0):
    from async_timeout import timeout as timeout_ctx
else:
    from asyncio import timeout as timeout_ctx  # type: ignore

from .base import (
    ClosableResponse,
    EmptyResponse,
    Header,
    Request,
    UnexpectedContentTypeError,
    build_query_parameters,
    is_expected_content_type,
    substitute_path_parameters,
)
from .context import set_context
from .deadline import Deadline
from .priority import Priority
from .transport import Transport
from .utils import try_parse_float

logger = logging.getLogger(__package__)


class AioHttpDnsResolver(aiohttp.abc.AbstractResolver):
    __slots__ = ("_resolver", "_results", "_interval", "_task", "_max_failures")

    def __init__(
        self,
        resolver: aiohttp.abc.AbstractResolver,
        *,
        interval: float = 30,
        max_failures: float = 3,
    ):
        if interval <= 0:
            raise RuntimeError("Interval should be positive")
        if max_failures <= 0:
            raise RuntimeError("Max failures should be positive")

        self._interval = interval
        self._resolver = resolver
        self._results: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
        self._task = asyncio.create_task(self._resolve())
        self._max_failures = max_failures

    def resolve_no_wait(self, host: str, port: int, family: int) -> list[dict[str, Any]] | None:
        return self._results.get((host, port, family))

    async def resolve(self, host: str, port: int, family: int) -> list[dict[str, Any]]:
        key = (host, port, family)
        addresses = self._results.get(key)
        if addresses is not None:
            return addresses
        addresses = await self._resolver.resolve(host, port, family)
        self._results[key] = addresses
        return addresses

    async def close(self) -> None:
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        await self._resolver.close()

    async def _resolve(self) -> None:
        failures_per_endpoint: dict[tuple[str, int, int], int] = {}
        while True:
            await asyncio.sleep(self._interval)

            keys_to_pop = []

            for key in list(self._results.keys()):
                try:
                    (h, p, f) = key
                    self._results[key] = await self._resolver.resolve(h, p, f)
                except Exception:
                    failures = failures_per_endpoint.pop(key, 0)
                    if failures + 1 >= self._max_failures:
                        keys_to_pop.append(key)
                    else:
                        failures_per_endpoint[key] = failures + 1
                else:
                    failures_per_endpoint.pop(key, 0)

            for key_to_pop in keys_to_pop:
                self._results.pop(key_to_pop, None)


class AioHttpTransport(Transport):
    __slots__ = (
        "_client_session",
        "_metrics_provider",
        "_network_errors_code",
        "_too_many_redirects_code",
        "_buffer_payload",
    )

    def __init__(
        self,
        client_session: aiohttp.ClientSession,
        *,
        metrics_provider: MetricsProvider | None = None,
        network_errors_code: int = 489,
        too_many_redirects_code: int = 488,
        buffer_payload: bool = True,
    ):
        if metrics_provider is not None:
            warnings.warn(
                "metrics_provider is deprecated, it will not be used, consider a migration to OpenTelemetry",
                DeprecationWarning,
            )

        self._client_session = client_session
        self._network_errors_code = network_errors_code
        self._buffer_payload = buffer_payload
        self._too_many_redirects_code = too_many_redirects_code

    async def send(self, endpoint: yarl.URL, request: Request, timeout: float) -> ClosableResponse:
        if not endpoint.is_absolute():
            raise RuntimeError("Base url should be absolute")

        method = request.method
        url = endpoint.join(substitute_path_parameters(request.url, request.path_parameters))
        if request.query_parameters is not None:
            url = url.update_query(build_query_parameters(request.query_parameters))
        headers = request.headers
        body = request.body
        allow_redirects = request.allow_redirects
        max_redirects = request.max_redirects

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
                allow_redirects=allow_redirects,
                max_redirects=max_redirects,
            )
            if self._buffer_payload:
                await response.read()  # force response to buffer its body
            return _AioHttpResponse(response)
        except aiohttp.TooManyRedirects as e:
            logger.warning(
                "Request %s %s has failed: too many redirects",
                method,
                url,
                exc_info=True,
                extra={
                    "request_method": method,
                    "request_url": url,
                },
            )

            headers = multidict.CIMultiDict[str]()
            for redirect_response in e.history:
                for location_header in redirect_response.headers.getall(Header.LOCATION):
                    headers.add(Header.LOCATION, location_header)
            return EmptyResponse(
                status=self._too_many_redirects_code,
                headers=multidict.CIMultiDictProxy[str](headers),
            )
        except aiohttp.ClientError:
            logger.warning(
                "Request %s %s has failed: network error",
                method,
                url,
                exc_info=True,
                extra={
                    "request_method": method,
                    "request_url": url,
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
                    "request_method": method,
                    "request_url": url,
                    "request_timeout": timeout,
                },
            )
            return EmptyResponse(status=408)


class _AioHttpResponse(ClosableResponse):
    __slots__ = ("_response",)

    def __init__(self, response: aiohttp.ClientResponse):
        self._response = response

    async def close(self) -> None:
        await self._response.release()

    @property
    def status(self) -> int:
        return self._response.status

    @property
    def headers(self) -> multidict.CIMultiDictProxy[str]:
        return self._response.headers

    async def json(
        self,
        *,
        encoding: str | None = None,
        loads: collections.abc.Callable[[str], Any] = json.loads,
        content_type: str | None = "application/json",
    ) -> Any:
        if content_type is not None:
            response_content_type = self._response.headers.get(Header.CONTENT_TYPE, "").lower()
            if not is_expected_content_type(response_content_type, content_type):
                raise UnexpectedContentTypeError(f"Expected {content_type}, actual {response_content_type}")

        return await self._response.json(encoding=encoding, loads=loads, content_type=None)

    async def read(self) -> bytes:
        return await self._response.read()

    async def text(self, encoding: str | None = None) -> str:
        return await self._response.text(encoding=encoding)


_HANDLER = collections.abc.Callable[
    [aiohttp.web_request.Request], collections.abc.Awaitable[aiohttp.web_response.StreamResponse]
]
_MIDDLEWARE = collections.abc.Callable[
    [aiohttp.web_request.Request, _HANDLER],
    collections.abc.Awaitable[aiohttp.web_response.StreamResponse],
]


def aiohttp_timeout(*, seconds: float) -> collections.abc.Callable[..., Any]:
    def wrapper(func: collections.abc.Callable[..., Any]) -> collections.abc.Callable[..., Any]:
        setattr(func, "__aio_request_timeout__", seconds)
        return func

    return wrapper


def aiohttp_middleware_factory(
    *,
    timeout: float = 20,
    priority: Priority = Priority.NORMAL,
    low_timeout_threshold: float = 0.005,
    metrics_provider: MetricsProvider | None = None,
    client_header_name: str | multidict.istr = Header.X_SERVICE_NAME,
    cancel_on_timeout: bool = False,
) -> _MIDDLEWARE:
    if metrics_provider is not None:
        warnings.warn(
            "metrics_provider is deprecated, it will not be used, consider a migration to OpenTelemetry",
            DeprecationWarning,
        )

    meter = opentelemetry.metrics.get_meter(__package__)  # type: ignore
    status_counter = meter.create_counter("aio_request_server_status")
    latency_histogram = meter.create_histogram("aio_request_server_latency")

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
        status_counter.add(1, tags)
        latency_histogram.record(elapsed, tags)

    @aiohttp.web_middlewares.middleware
    async def middleware(
        request: aiohttp.web_request.Request, handler: _HANDLER
    ) -> aiohttp.web_response.StreamResponse:
        deadline = _get_deadline(request) or _get_deadline_from_handler(request) or Deadline.from_timeout(timeout)
        started_at = time.perf_counter()

        try:
            response: aiohttp.web_response.StreamResponse | None
            if deadline.expired or deadline.timeout <= low_timeout_threshold:
                response = aiohttp.web_response.Response(status=408)
            else:
                with set_context(deadline=deadline, priority=_get_priority(request) or priority):
                    if not cancel_on_timeout:
                        response = await handler(request)
                    else:
                        try:
                            async with timeout_ctx(deadline.timeout):
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


def _get_deadline(request: aiohttp.web_request.Request) -> Deadline | None:
    timeout = try_parse_float(request.headers.get(Header.X_REQUEST_TIMEOUT))
    if timeout is not None:
        return Deadline.from_timeout(timeout)

    return Deadline.try_parse(request.headers.get(Header.X_REQUEST_DEADLINE_AT))


def _get_priority(request: aiohttp.web_request.Request) -> Priority | None:
    return Priority.try_parse(request.headers.get(Header.X_REQUEST_PRIORITY))


def _get_deadline_from_handler(
    request: aiohttp.web_request.Request,
) -> Deadline | None:
    handler = request.match_info.handler
    timeout = getattr(handler, "__aio_request_timeout__", None)
    if timeout is None and _is_subclass(handler, aiohttp.web.View):
        method_handler = getattr(handler, request.method.lower(), None)
        if method_handler is not None:
            timeout = getattr(method_handler, "__aio_request_timeout__", None)

    return Deadline.from_timeout(float(timeout)) if timeout is not None else None


def _is_subclass(cls: Any, cls_info: type) -> bool:
    try:
        return issubclass(cls, cls_info)
    except TypeError:
        return False
