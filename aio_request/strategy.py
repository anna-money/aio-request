import abc
import asyncio
from typing import Any, AsyncContextManager, Callable, Dict, List, Optional, Set, Union

from .base import ClosableResponse, EmptyResponse, Request, Response
from .deadline import Deadline
from .delays_provider import linear_delays
from .priority import Priority
from .request_sender import RequestSender
from .response_classifier import DefaultResponseClassifier, ResponseClassifier, ResponseVerdict
from .utils import close_many


class RequestStrategy(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def request(
        self,
        request: Request,
        deadline: Optional[Union[float, Deadline]] = None,
        priority: Optional[Union[Priority]] = None,
    ) -> AsyncContextManager[Response]:
        ...


class MethodBasedStrategy(RequestStrategy):
    __slots__ = ("_strategy_by_method",)

    def __init__(self, strategy_by_method: Dict[str, RequestStrategy]):
        self._strategy_by_method = strategy_by_method

    def request(
        self,
        request: Request,
        deadline: Optional[Union[float, Deadline]] = None,
        priority: Optional[Union[Priority]] = None,
    ) -> AsyncContextManager[Response]:
        return self._strategy_by_method[request.method].request(request, deadline)


class RequestStrategiesFactory:
    __slots__ = ("_request_sender", "_response_classifier", "_timeout", "_priority")

    def __init__(
        self,
        request_sender: RequestSender,
        response_classifier: Optional[ResponseClassifier] = None,
        timeout: float = 60 * 5,
        priority: Priority = Priority.NORMAL,
    ):
        self._request_sender = request_sender
        self._response_classifier = response_classifier or DefaultResponseClassifier()
        self._timeout = timeout
        self._priority = priority

    def sequential(
        self, *, attempts_count: int = 3, delays_provider: Callable[[int], float] = linear_delays()
    ) -> RequestStrategy:
        return _RequestStrategy(
            lambda request, deadline, priority: _SequentialRequestStrategy(
                request_sender=self._request_sender,
                response_classifier=self._response_classifier,
                request=request,
                deadline=self._get_deadline(deadline),
                attempts_count=attempts_count,
                delays_provider=delays_provider,
                priority=priority or self._priority,
            )
        )

    def parallel(
        self, *, attempts_count: int = 3, delays_provider: Callable[[int], float] = linear_delays()
    ) -> RequestStrategy:
        return _RequestStrategy(
            lambda request, deadline, priority: _ParallelRequestStrategy(
                request_sender=self._request_sender,
                response_classifier=self._response_classifier,
                request=request,
                deadline=self._get_deadline(deadline),
                attempts_count=attempts_count,
                delays_provider=delays_provider,
                priority=priority or self._priority,
            )
        )

    def _get_deadline(self, deadline: Optional[Union[float, Deadline]]) -> Deadline:
        if deadline is None:
            return Deadline.from_timeout(self._timeout)
        if isinstance(deadline, float):
            return Deadline.from_timeout(deadline)
        return deadline


class _RequestStrategy(RequestStrategy):
    __slots__ = ("_create_strategy",)

    def __init__(
        self,
        create_strategy: Callable[
            [Request, Optional[Union[float, Deadline]], Optional[Priority]], AsyncContextManager[Response]
        ],
    ):
        self._create_strategy = create_strategy

    def request(
        self,
        request: Request,
        deadline: Optional[Union[float, Deadline]] = None,
        priority: Optional[Union[Priority]] = None,
    ) -> AsyncContextManager[Response]:
        return self._create_strategy(request, deadline, priority)


class _SequentialRequestStrategy:
    __slots__ = (
        "_responses",
        "_request_sender",
        "_request",
        "_response_classifier",
        "_attempts_count",
        "_deadline",
        "_priority",
        "_delays_provider",
    )

    def __init__(
        self,
        *,
        request_sender: RequestSender,
        response_classifier: ResponseClassifier,
        request: Request,
        deadline: Deadline,
        priority: Priority,
        attempts_count: int,
        delays_provider: Callable[[int], float],
    ):
        if attempts_count < 1:
            raise RuntimeError("Attempts count should be >= 1")

        self._delays_provider = delays_provider
        self._deadline = deadline
        self._priority = priority
        self._attempts_count = attempts_count
        self._request = request
        self._request_sender = request_sender
        self._responses: List[ClosableResponse] = []
        self._response_classifier = response_classifier

    async def __aenter__(self) -> Response:
        for attempt in range(self._attempts_count):
            if self._deadline.expired:
                return EmptyResponse(status=408)

            response = await self._request_sender.send(self._request, self._deadline, self._priority)
            self._responses.append(response)
            if self._response_classifier.classify(response) == ResponseVerdict.ACCEPT:
                return response

            if attempt + 1 == self._attempts_count:
                break

            retry_delay = self._delays_provider(attempt + 1)
            if self._deadline.timeout < retry_delay:
                break

            await asyncio.sleep(retry_delay)

        assert len(self._responses) > 0

        return self._responses[-1]

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        await asyncio.shield(close_many(self._responses))
        return False


class _ParallelRequestStrategy:
    __slots__ = (
        "_responses",
        "_request_sender",
        "_request",
        "_response_classifier",
        "_deadline",
        "_priority",
        "_attempts_count",
        "_delays_provider",
    )

    def __init__(
        self,
        request_sender: RequestSender,
        request: Request,
        response_classifier: ResponseClassifier,
        *,
        deadline: Deadline,
        priority: Priority,
        attempts_count: int,
        delays_provider: Callable[[int], float],
    ):
        if attempts_count < 1:
            raise RuntimeError("Attempts count should be >= 1")

        self._attempts_count = attempts_count
        self._deadline = deadline
        self._priority = priority
        self._request = request
        self._request_sender = request_sender
        self._responses: List[ClosableResponse] = []
        self._response_classifier = response_classifier
        self._delays_provider = delays_provider

    async def __aenter__(self) -> Response:
        pending_tasks: Set[asyncio.Future[ClosableResponse]] = set()
        for attempt in range(0, self._attempts_count):
            pending_tasks.add(asyncio.create_task(self._schedule_request(attempt)))

        try:
            while pending_tasks:
                completed_tasks, pending_tasks = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED)
                for completed_task in completed_tasks:
                    response = await completed_task
                    self._responses.append(response)
                    if self._response_classifier.classify(response) == ResponseVerdict.ACCEPT:
                        return response
        finally:
            for pending_task in pending_tasks:
                pending_task.cancel()

        assert len(self._responses) > 0
        return self._responses[-1]

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        await asyncio.shield(close_many(self._responses))
        return False

    async def _schedule_request(self, attempt: int) -> ClosableResponse:
        if attempt > 0:
            await asyncio.sleep(min(self._delays_provider(attempt), self._deadline.timeout))
        if self._deadline.expired:
            return EmptyResponse(status=408)
        return await self._request_sender.send(self._request, self._deadline, self._priority)
