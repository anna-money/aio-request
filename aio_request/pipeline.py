import abc
import collections.abc

import multidict
import yarl

from .base import ClosableResponse, EmptyResponse, Header, Request
from .circuit_breaker import CircuitBreaker
from .deadline import Deadline
from .priority import Priority
from .request import RequestEnricher
from .response_classifier import ResponseClassifier, ResponseVerdict
from .transport import Transport

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

    def __init__(self, low_timeout_threshold: float):
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
    __slots__ = ("__transport", "__emit_system_headers", "__request_enricher")

    def __init__(
        self,
        transport: Transport,
        *,
        emit_system_headers: bool,
        request_enricher: RequestEnricher | None,
    ):
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
                    Header.X_REQUEST_DEADLINE_AT: str(deadline),  # for backward compatibility
                    Header.X_REQUEST_PRIORITY: str(priority),
                    Header.X_REQUEST_TIMEOUT: str(deadline.timeout),
                }
            )

        if self.__request_enricher is not None:
            request = await self.__request_enricher(request, self.__emit_system_headers)

        return await self.__transport.send(endpoint, request, deadline.timeout)


class CircuitBreakerModule(RequestModule):
    __slots__ = ("__circuit_breaker", "__fallback", "__response_classifier")

    def __init__(
        self,
        circuit_breaker: CircuitBreaker[yarl.URL, ClosableResponse],
        *,
        status_code: int = 502,
        response_classifier: ResponseClassifier,
    ):
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
        raise NotImplementedError()

    def _execute_module(m: RequestModule, n: NextModuleFunc) -> NextModuleFunc:
        return lambda e, r, d, p: m.execute(n, endpoint=e, request=r, deadline=d, priority=p)

    pipeline: NextModuleFunc = _unsupported
    for module in reversed(modules):
        if isinstance(module, BypassModule):
            continue
        pipeline = _execute_module(module, pipeline)
    return pipeline
