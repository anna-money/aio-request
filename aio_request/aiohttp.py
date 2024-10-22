import asyncio
import collections.abc
import contextlib
import json
import logging
import socket
import time
import warnings
from typing import Any

import aiohttp
import aiohttp.abc
import aiohttp.typedefs
import aiohttp.web
import aiohttp.web_exceptions
import aiohttp.web_middlewares
import aiohttp.web_request
import aiohttp.web_response
import multidict
import yarl

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
from .deprecated import MetricsProvider
from .priority import Priority
from .transport import Transport
from .utils import try_parse_float

try:
    import prometheus_client as prom

    latency_histogram = prom.Histogram(
        "aio_request_server_latency",
        "Duration of HTTP server requests.",
        labelnames=(
            "request_client",
            "request_method",
            "request_path",
            "response_status",
        ),
        buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 5.0, 10.0, 15.0, 20.0),
    )

    def capture_metrics(*, method: str, path: str, client: str, status: int, started_at: float) -> None:
        label_values = (
            client,
            method,
            path,
            str(status),
        )
        elapsed = max(0.0, time.perf_counter() - started_at)
        latency_histogram.labels(*label_values).observe(elapsed)

except ImportError:

    def capture_metrics(*, method: str, path: str, client: str, status: int, started_at: float) -> None:
        pass


logger = logging.getLogger(__package__)


class AioHttpDnsResolver(aiohttp.abc.AbstractResolver):
    __slots__ = ("__resolver", "__results", "__interval", "__task", "__max_failures")

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

        self.__interval = interval
        self.__resolver = resolver
        self.__results: dict[tuple[str, int, socket.AddressFamily], list[aiohttp.abc.ResolveResult]] = {}
        self.__task = asyncio.create_task(self._resolve())
        self.__max_failures = max_failures

    def resolve_no_wait(
        self, host: str, port: int = 0, family: socket.AddressFamily = socket.AF_INET
    ) -> list[aiohttp.abc.ResolveResult] | None:
        return self.__results.get((host, port, family))

    async def resolve(
        self, host: str, port: int = 0, family: socket.AddressFamily = socket.AF_INET
    ) -> list[aiohttp.abc.ResolveResult]:
        key = (host, port, family)
        addresses = self.__results.get(key)
        if addresses is not None:
            return addresses
        addresses = await self.__resolver.resolve(host, port, family)
        self.__results[key] = addresses
        return addresses

    async def close(self) -> None:
        self.__task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self.__task
        await self.__resolver.close()

    async def _resolve(self) -> None:
        failures_per_endpoint: dict[tuple[str, int, socket.AddressFamily], int] = {}
        while True:
            await asyncio.sleep(self.__interval)

            keys_to_pop = []

            for key in list(self.__results.keys()):
                try:
                    (h, p, f) = key
                    self.__results[key] = await self.__resolver.resolve(h, p, f)
                except Exception:
                    failures = failures_per_endpoint.pop(key, 0)
                    if failures + 1 >= self.__max_failures:
                        keys_to_pop.append(key)
                    else:
                        failures_per_endpoint[key] = failures + 1
                else:
                    failures_per_endpoint.pop(key, 0)

            for key_to_pop in keys_to_pop:
                self.__results.pop(key_to_pop, None)


class AioHttpTransport(Transport):
    __slots__ = (
        "__client_session",
        "__network_errors_code",
        "__too_many_redirects_code",
        "__buffer_payload",
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

        self.__client_session = client_session
        self.__network_errors_code = network_errors_code
        self.__buffer_payload = buffer_payload
        self.__too_many_redirects_code = too_many_redirects_code

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
            response = await self.__client_session.request(
                method,
                url,
                headers=headers,
                data=body,
                timeout=aiohttp.ClientTimeout(total=timeout),
                allow_redirects=allow_redirects,
                max_redirects=max_redirects,
            )
            if self.__buffer_payload:
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
                status=self.__too_many_redirects_code,
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
            return EmptyResponse(status=self.__network_errors_code)
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
    __slots__ = ("__response",)

    def __init__(self, response: aiohttp.ClientResponse):
        self.__response = response

    async def close(self) -> None:
        await self.__response.release()

    @property
    def status(self) -> int:
        return self.__response.status

    @property
    def headers(self) -> multidict.CIMultiDictProxy[str]:
        return self.__response.headers

    async def json(
        self,
        *,
        encoding: str | None = None,
        loads: collections.abc.Callable[[str], Any] = json.loads,
        content_type: str | None = "application/json",
    ) -> Any:
        if content_type is not None:
            response_content_type = self.__response.headers.get(Header.CONTENT_TYPE, "").lower()
            if not is_expected_content_type(response_content_type, content_type):
                raise UnexpectedContentTypeError(f"Expected {content_type}, actual {response_content_type}")

        return await self.__response.json(encoding=encoding, loads=loads, content_type=None)

    async def read(self) -> bytes:
        return await self.__response.read()

    async def text(self, encoding: str | None = None) -> str:
        return await self.__response.text(encoding=encoding)


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
) -> aiohttp.typedefs.Middleware:
    if metrics_provider is not None:
        warnings.warn(
            "metrics_provider is deprecated, it will not be used, consider a migration to OpenTelemetry",
            DeprecationWarning,
        )

    @aiohttp.web_middlewares.middleware
    async def middleware(
        request: aiohttp.web_request.Request, handler: aiohttp.typedefs.Handler
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
                            async with asyncio.timeout(deadline.timeout):
                                response = await handler(request)
                        except asyncio.TimeoutError:
                            response = aiohttp.web_response.Response(status=408)

            capture_metrics(
                method=request.method,
                path=_get_route_path(request),
                client=request.headers.get(client_header_name, "unknown").lower(),
                status=response.status,
                started_at=started_at,
            )

            return response
        except asyncio.CancelledError:
            capture_metrics(
                method=request.method,
                path=_get_route_path(request),
                client=request.headers.get(client_header_name, "unknown").lower(),
                status=499,
                started_at=started_at,
            )
            raise
        except aiohttp.web_exceptions.HTTPException as e:
            capture_metrics(
                method=request.method,
                path=_get_route_path(request),
                client=request.headers.get(client_header_name, "unknown").lower(),
                status=e.status,
                started_at=started_at,
            )
            raise
        except Exception:
            capture_metrics(
                method=request.method,
                path=_get_route_path(request),
                client=request.headers.get(client_header_name, "unknown").lower(),
                status=500,
                started_at=started_at,
            )
            raise

    return middleware


def _get_route_path(request: aiohttp.web_request.Request) -> str:
    return request.match_info.route.resource.canonical if request.match_info.route.resource else request.path


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
