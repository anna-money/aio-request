import abc
import collections.abc

import multidict
import yarl

from .base import ClosableResponse, EmptyResponse, Header, Request
from .circuit_breaker import CircuitBreaker
from .deadline import Deadline
from .priority import Priority
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
    ) -> ClosableResponse:
        ...


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
    __slots__ = ("_low_timeout_threshold",)

    def __init__(self, low_timeout_threshold: float):
        self._low_timeout_threshold = low_timeout_threshold

    async def execute(
        self,
        next: NextModuleFunc,
        *,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ClosableResponse:
        if deadline.expired or deadline.timeout < self._low_timeout_threshold:
            return EmptyResponse(status=408)

        return await next(endpoint, request, deadline, priority)


class TransportModule(RequestModule):
    __slots__ = ("_transport", "_emit_system_headers", "_request_enricher")

    def __init__(
        self,
        transport: Transport,
        *,
        emit_system_headers: bool,
        request_enricher: collections.abc.Callable[[Request, bool], collections.abc.Awaitable[Request]] | None,
    ):
        self._transport = transport
        self._emit_system_headers = emit_system_headers
        self._request_enricher = request_enricher

    async def execute(
        self,
        _: NextModuleFunc,
        *,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ClosableResponse:
        if self._emit_system_headers:
            request = request.update_headers(
                {
                    Header.X_REQUEST_DEADLINE_AT: str(deadline),  # for backward compatibility
                    Header.X_REQUEST_PRIORITY: str(priority),
                    Header.X_REQUEST_TIMEOUT: str(deadline.timeout),
                }
            )

        request = (
            await self._request_enricher(request, self._emit_system_headers)
            if self._request_enricher is not None
            else request
        )

        return await self._transport.send(endpoint, request, deadline.timeout)


class CircuitBreakerModule(RequestModule):
    __slots__ = ("_circuit_breaker", "_fallback", "_response_classifier")

    def __init__(
        self,
        circuit_breaker: CircuitBreaker[yarl.URL, ClosableResponse],
        *,
        status_code: int = 502,
        response_classifier: ResponseClassifier,
    ):
        self._circuit_breaker = circuit_breaker
        self._response_classifier = response_classifier

        headers = multidict.CIMultiDict[str]()
        headers[Header.X_DO_NOT_RETRY] = "1"
        headers[Header.X_CIRCUIT_BREAKER] = "1"
        self._fallback = EmptyResponse(
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
        return await self._circuit_breaker.execute(
            scope=endpoint,
            operation=lambda: next(endpoint, request, deadline, priority),
            fallback=self._fallback,
            is_successful=lambda x: _response_verdict_to_bool(self._response_classifier.classify(x)),
        )


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


def _response_verdict_to_bool(response_verdict: ResponseVerdict) -> bool:
    match response_verdict:
        case ResponseVerdict.ACCEPT:
            return True
        case ResponseVerdict.REJECT:
            return False
