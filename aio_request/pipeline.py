import abc
import asyncio
import collections.abc
import logging

import multidict
import yarl

from .base import ClosableResponse, EmptyResponse, Header, Request
from .circuit_breaker import CircuitBreaker
from .deadline import Deadline
from .priority import Priority
from .request import AsyncRequestEnricher, RequestEnricher
from .response_classifier import ResponseClassifier, ResponseVerdict
from .transport import Transport

logger = logging.getLogger(__name__)

try:
    import prometheus_client as prom

    latency_histogram = prom.Histogram(
        "aio_request_transport_latency",
        "Duration of transport requests.",
        labelnames=(
            "request_endpoint",
            "request_method",
            "request_path",
            "response_status",
        ),
        buckets=(
            0.005,
            0.01,
            0.025,
            0.05,
            0.075,
            0.1,
            0.15,
            0.2,
            0.25,
            0.3,
            0.35,
            0.4,
            0.45,
            0.5,
            0.75,
            1.0,
            5.0,
            10.0,
            15.0,
            20.0,
        ),
    )

    def capture_metrics(*, endpoint: yarl.URL, request: Request, status: int, elapsed: float) -> None:
        label_values = (
            endpoint.human_repr(),
            request.method,
            request.url.path,
            str(status),
        )
        latency_histogram.labels(*label_values).observe(elapsed)

except ImportError:

    def capture_metrics(*, endpoint: yarl.URL, request: Request, status: int, elapsed: float) -> None:
        pass


NextModuleFunc = collections.abc.Callable[
    [yarl.URL, Request, Deadline, Priority], collections.abc.Awaitable[ClosableResponse]
]


class RequestModule(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def execute(
        self,
        next: NextModuleFunc,
        *,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ClosableResponse: ...


class BypassModule(RequestModule):
    __slots__ = ()

    async def execute(
        self,
        next: NextModuleFunc,
        *,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ClosableResponse:
        return await next(endpoint, request, deadline, priority)


class LowTimeoutModule(RequestModule):
    __slots__ = ("__low_timeout_threshold", "__timeout_response")

    def __init__(self, low_timeout_threshold: float) -> None:
        self.__low_timeout_threshold = low_timeout_threshold

        headers = multidict.CIMultiDict[str]()
        headers[Header.X_DO_NOT_RETRY] = "1"
        self.__timeout_response = EmptyResponse(
            status=408,
            headers=multidict.CIMultiDictProxy[str](headers),
        )

    async def execute(
        self,
        next: NextModuleFunc,
        *,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ClosableResponse:
        if deadline.expired or deadline.timeout < self.__low_timeout_threshold:
            return self.__timeout_response

        return await next(endpoint, request, deadline, priority)


class TransportModule(RequestModule):
    __slots__ = ("__emit_system_headers", "__request_enricher", "__transport")

    def __init__(
        self,
        transport: Transport,
        *,
        emit_system_headers: bool,
        request_enricher: AsyncRequestEnricher | RequestEnricher | None,
    ) -> None:
        self.__transport = transport
        self.__emit_system_headers = emit_system_headers
        self.__request_enricher = request_enricher

    async def execute(
        self,
        next: NextModuleFunc,
        *,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ClosableResponse:
        if self.__emit_system_headers:
            request = request.update_headers(
                {
                    Header.X_REQUEST_PRIORITY: str(priority),
                    Header.X_REQUEST_TIMEOUT: str(deadline.timeout),
                }
            )

        if self.__request_enricher is not None:
            enriched_request = self.__request_enricher(request)
            if asyncio.iscoroutine(enriched_request):
                enriched_request = await enriched_request
            request = enriched_request  # type: ignore

        response = await self.__transport.send(endpoint, request, deadline.timeout)
        if response.elapsed >= 0:
            capture_metrics(endpoint=endpoint, request=request, status=response.status, elapsed=response.elapsed)
        else:
            logger.warning("Response elapsed time is not calculated, please implement it, metrics will not be captured")
        return response


class CircuitBreakerModule(RequestModule):
    __slots__ = ("__circuit_breaker", "__fallback", "__response_classifier")

    def __init__(
        self,
        circuit_breaker: CircuitBreaker[yarl.URL, ClosableResponse],
        *,
        status_code: int = 502,
        response_classifier: ResponseClassifier,
    ) -> None:
        self.__circuit_breaker = circuit_breaker
        self.__response_classifier = response_classifier

        headers = multidict.CIMultiDict[str]()
        headers[Header.X_DO_NOT_RETRY] = "1"
        headers[Header.X_CIRCUIT_BREAKER] = "1"
        self.__fallback = EmptyResponse(
            status=status_code,
            headers=multidict.CIMultiDictProxy[str](headers),
        )

    async def execute(
        self,
        next: NextModuleFunc,
        *,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ClosableResponse:
        return await self.__circuit_breaker.execute(
            scope=endpoint,
            operation=lambda: next(endpoint, request, deadline, priority),
            fallback=self.__fallback,
            is_successful=lambda x: self.__response_verdict_to_bool(self.__response_classifier.classify(x)),
        )

    @staticmethod
    def __response_verdict_to_bool(response_verdict: ResponseVerdict) -> bool:
        match response_verdict:
            case ResponseVerdict.ACCEPT:
                return True
            case ResponseVerdict.REJECT:
                return False


def build_pipeline(modules: list[RequestModule]) -> NextModuleFunc:
    async def _unsupported(
        _: yarl.URL,
        __: Request,
        ___: Deadline,
        ____: Priority,
    ) -> ClosableResponse:
        raise NotImplementedError

    def _execute_module(m: RequestModule, n: NextModuleFunc) -> NextModuleFunc:
        return lambda e, r, d, p: m.execute(n, endpoint=e, request=r, deadline=d, priority=p)

    pipeline: NextModuleFunc = _unsupported
    for module in reversed(modules):
        if isinstance(module, BypassModule):
            continue
        pipeline = _execute_module(module, pipeline)
    return pipeline
