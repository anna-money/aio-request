import abc
import asyncio
from typing import Any, AsyncContextManager, Callable, Dict, List, Set, Union

import yarl

from .base import ClosableResponse, EmptyResponse, Header, Request, Response
from .deadline import Deadline
from .delays_provider import linear_delays
from .priority import Priority
from .request_sender import RequestSender
from .response_classifier import ResponseClassifier, ResponseVerdict
from .utils import close_many


class RequestStrategy(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def request(
        self,
        request: Request,
        deadline: Deadline,
        priority: Priority = Priority.NORMAL,
    ) -> AsyncContextManager[Response]:
        ...


class MethodBasedStrategy(RequestStrategy):
    __slots__ = ("_strategy_by_method",)

    def __init__(self, strategy_by_method: Dict[str, RequestStrategy]):
        self._strategy_by_method = strategy_by_method

    def request(
        self,
        request: Request,
        deadline: Deadline,
        priority: Priority = Priority.NORMAL,
    ) -> AsyncContextManager[Response]:
        return self._strategy_by_method[request.method].request(request, deadline, priority)


class RequestStrategiesFactory:
    __slots__ = (
        "_request_sender",
        "service_url",
        "_response_classifier",
        "_emit_system_headers",
        "_low_timeout_threshold",
    )

    def __init__(
        self,
        request_sender: RequestSender,
        service_url: Union[str, yarl.URL],
        response_classifier: ResponseClassifier,
        emit_system_headers: bool = True,
        low_timeout_threshold: float = 0.005,
    ):
        self._request_sender = request_sender
        self.service_url = yarl.URL(service_url) if isinstance(service_url, str) else service_url
        self._response_classifier = response_classifier
        self._low_timeout_threshold = low_timeout_threshold
        self._emit_system_headers = emit_system_headers

    def sequential(
        self, *, attempts_count: int = 3, delays_provider: Callable[[int], float] = linear_delays()
    ) -> RequestStrategy:
        return _RequestStrategy(
            lambda request, deadline, priority: _SequentialRequestStrategy(
                request_sender=self._request_sender,
                service_url=self.service_url,
                response_classifier=self._response_classifier,
                request=request,
                deadline=deadline,
                attempts_count=attempts_count,
                delays_provider=delays_provider,
                priority=priority,
                emit_system_headers=self._emit_system_headers,
                low_timeout_threshold=self._low_timeout_threshold,
            ),
        )

    def parallel(
        self, *, attempts_count: int = 3, delays_provider: Callable[[int], float] = linear_delays()
    ) -> RequestStrategy:
        return _RequestStrategy(
            lambda request, deadline, priority: _ParallelRequestStrategy(
                request_sender=self._request_sender,
                service_url=self.service_url,
                response_classifier=self._response_classifier,
                request=request,
                deadline=deadline,
                attempts_count=attempts_count,
                delays_provider=delays_provider,
                priority=priority,
                emit_system_headers=self._emit_system_headers,
                low_timeout_threshold=self._low_timeout_threshold,
            ),
        )


class _RequestStrategy(RequestStrategy):
    __slots__ = ("_create_strategy",)

    def __init__(
        self,
        create_strategy: Callable[[Request, Deadline, Priority], AsyncContextManager[Response]],
    ):
        self._create_strategy = create_strategy

    def request(
        self,
        request: Request,
        deadline: Deadline,
        priority: Priority = Priority.NORMAL,
    ) -> AsyncContextManager[Response]:
        return self._create_strategy(request, deadline, priority)


class _RequestStrategyBase(abc.ABC):
    __slots__ = (
        "_request_sender",
        "_service_url",
        "_request",
        "_deadline",
        "_priority",
        "_responses",
        "_low_timeout_threshold",
        "_emit_system_headers",
    )

    def __init__(
        self,
        request_sender: RequestSender,
        *,
        service_url: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
        emit_system_headers: bool,
        low_timeout_threshold: float,
    ):
        self._low_timeout_threshold = low_timeout_threshold
        self._emit_system_headers = emit_system_headers
        self._priority = priority
        self._deadline = deadline
        self._request = request
        self._service_url = service_url
        self._request_sender = request_sender
        self._responses: List[ClosableResponse] = []

    @abc.abstractmethod
    async def __aenter__(self) -> Response:
        pass

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        await asyncio.shield(close_many(self._responses))
        return False

    async def _send_request(self) -> Response:
        if self._deadline.expired or self._deadline.timeout < self._low_timeout_threshold:
            response: ClosableResponse = EmptyResponse(status=408)
        else:
            request = self._request
            if self._emit_system_headers:
                request = request.update_headers(
                    {
                        Header.X_REQUEST_DEADLINE_AT: str(self._deadline),
                        Header.X_REQUEST_PRIORITY: str(self._priority),
                    }
                )
            response = await self._request_sender.send(self._service_url, request, self._deadline.timeout)
        self._responses.append(response)
        return response

    @property
    def _last_response(self) -> Response:
        assert len(self._responses) > 0

        return self._responses[-1]


class _SequentialRequestStrategy(_RequestStrategyBase):
    __slots__ = (
        "_response_classifier",
        "_attempts_count",
        "_delays_provider",
    )

    def __init__(
        self,
        *,
        request_sender: RequestSender,
        service_url: yarl.URL,
        response_classifier: ResponseClassifier,
        request: Request,
        deadline: Deadline,
        priority: Priority,
        attempts_count: int,
        delays_provider: Callable[[int], float],
        emit_system_headers: bool,
        low_timeout_threshold: float,
    ):
        super().__init__(
            request_sender,
            service_url=service_url,
            request=request,
            deadline=deadline,
            priority=priority,
            emit_system_headers=emit_system_headers,
            low_timeout_threshold=low_timeout_threshold,
        )
        if attempts_count < 1:
            raise RuntimeError("Attempts count should be >= 1")

        self._response_classifier = response_classifier
        self._delays_provider = delays_provider
        self._attempts_count = attempts_count

    async def __aenter__(self) -> Response:
        for attempt in range(self._attempts_count):
            response = await self._send_request()
            if self._response_classifier.classify(response) == ResponseVerdict.ACCEPT:
                return response
            if attempt + 1 == self._attempts_count:
                break
            retry_delay = self._delays_provider(attempt + 1)
            if self._deadline.timeout < retry_delay:
                break
            await asyncio.sleep(retry_delay)
        return self._last_response


class _ParallelRequestStrategy(_RequestStrategyBase):
    __slots__ = (
        "_response_classifier",
        "_attempts_count",
        "_delays_provider",
    )

    def __init__(
        self,
        request_sender: RequestSender,
        service_url: yarl.URL,
        request: Request,
        response_classifier: ResponseClassifier,
        *,
        deadline: Deadline,
        priority: Priority,
        attempts_count: int,
        delays_provider: Callable[[int], float],
        emit_system_headers: bool = True,
        low_timeout_threshold: float = 0.005,
    ):
        super().__init__(
            request_sender,
            service_url=service_url,
            request=request,
            deadline=deadline,
            priority=priority,
            emit_system_headers=emit_system_headers,
            low_timeout_threshold=low_timeout_threshold,
        )
        if attempts_count < 1:
            raise RuntimeError("Attempts count should be >= 1")

        self._response_classifier = response_classifier
        self._attempts_count = attempts_count
        self._delays_provider = delays_provider

    async def __aenter__(self) -> Response:
        pending_tasks: Set[asyncio.Future[Response]] = set()
        for attempt in range(0, self._attempts_count):
            pending_tasks.add(asyncio.create_task(self._schedule_request(attempt)))

        try:
            while pending_tasks:
                completed_tasks, pending_tasks = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED)
                for completed_task in completed_tasks:
                    response = await completed_task
                    if self._response_classifier.classify(response) == ResponseVerdict.ACCEPT:
                        return response
        finally:
            for pending_task in pending_tasks:
                pending_task.cancel()

        return self._last_response

    async def _schedule_request(self, attempt: int) -> Response:
        if attempt > 0:
            await asyncio.sleep(min(self._delays_provider(attempt), self._deadline.timeout))
        return await self._send_request()
