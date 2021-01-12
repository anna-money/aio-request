import asyncio
from abc import ABC, abstractmethod
from asyncio import Future
from contextlib import suppress
from typing import AsyncContextManager, Callable, List, Any, Dict, Set, Union, Optional

from .base import EmptyResponse
from .deadline import Deadline
from .delays_provider import linear_delays
from .base import Response, Request, ClosableResponse
from .request_sender import RequestSender
from .response_classifier import ResponseVerdict, ResponseClassifier, DefaultResponseClassifier


class RequestStrategy(ABC):
    __slots__ = ()

    @abstractmethod
    def request(
        self, request: Request, deadline: Optional[Union[float, Deadline]] = None
    ) -> AsyncContextManager[Response]:
        ...


class MethodBasedStrategy(RequestStrategy):
    __slots__ = ("_strategy_by_method",)

    def __init__(self, strategy_by_method: Dict[str, RequestStrategy]):
        self._strategy_by_method = strategy_by_method

    def request(
        self, request: Request, deadline: Optional[Union[float, Deadline]] = None
    ) -> AsyncContextManager[Response]:
        return self._strategy_by_method[request.method].request(request, deadline)


class RequestStrategiesFactory:
    __slots__ = ("_request_sender", "_response_classifier", "_default_deadline_seconds")

    def __init__(
        self,
        request_sender: RequestSender,
        response_classifier: Optional[ResponseClassifier] = None,
        default_deadline_seconds: float = 60 * 5,
    ):
        self._request_sender = request_sender
        self._response_classifier = response_classifier or DefaultResponseClassifier()
        self._default_deadline_seconds = default_deadline_seconds

    def sequential(
        self, *, attempts_count: int = 3, delays_provider: Callable[[int], float] = linear_delays()
    ) -> RequestStrategy:
        return _RequestStrategy(
            lambda request, deadline: _SequentialRequestStrategy(
                request_sender=self._request_sender,
                response_classifier=self._response_classifier,
                request=request,
                deadline=self._get_deadline(deadline),
                attempts_count=attempts_count,
                delays_provider=delays_provider,
            )
        )

    def parallel(
        self, *, attempts_count: int = 3, delays_provider: Callable[[int], float] = linear_delays()
    ) -> RequestStrategy:
        return _RequestStrategy(
            lambda request, deadline: _ParallelRequestStrategy(
                request_sender=self._request_sender,
                response_classifier=self._response_classifier,
                request=request,
                deadline=self._get_deadline(deadline),
                attempts_count=attempts_count,
                delays_provider=delays_provider,
            )
        )

    def _get_deadline(self, deadline: Optional[Union[float, Deadline]]) -> Deadline:
        if deadline is None:
            return Deadline.after_seconds(self._default_deadline_seconds)
        if isinstance(deadline, float):
            return Deadline.after_seconds(deadline)
        return deadline


class _RequestStrategy(RequestStrategy):
    __slots__ = ("_create_strategy",)

    def __init__(
        self, create_strategy: Callable[[Request, Optional[Union[float, Deadline]]], AsyncContextManager[Response]]
    ):
        self._create_strategy = create_strategy

    def request(
        self, request: Request, deadline: Optional[Union[float, Deadline]] = None
    ) -> AsyncContextManager[Response]:
        return self._create_strategy(request, deadline)


class _SequentialRequestStrategy:
    __slots__ = (
        "_responses",
        "_request_sender",
        "_request",
        "_response_classifier",
        "_attempts_count",
        "_deadline",
        "_delays_provider",
    )

    def __init__(
        self,
        *,
        request_sender: RequestSender,
        response_classifier: ResponseClassifier,
        request: Request,
        deadline: Deadline,
        attempts_count: int,
        delays_provider: Callable[[int], float],
    ):
        if attempts_count < 1:
            raise RuntimeError("Attempts count should be >= 1")

        self._delays_provider = delays_provider
        self._deadline = deadline
        self._attempts_count = attempts_count
        self._request = request
        self._request_sender = request_sender
        self._responses: List[ClosableResponse] = []
        self._response_classifier = response_classifier

    async def __aenter__(self) -> Response:
        for attempt in range(self._attempts_count):
            if self._deadline.expired:
                return EmptyResponse(status=408)

            response = await self._request_sender.send(self._request, self._deadline)
            self._responses.append(response)
            if self._response_classifier.classify(response) == ResponseVerdict.ACCEPT:
                return response

            await asyncio.sleep(min(self._delays_provider(attempt), self._deadline.timeout))

        assert len(self._responses) > 0

        return self._responses[-1]

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        while self._responses:
            response = self._responses.pop()
            with suppress(Exception):
                await response.close()
        return False


class _ParallelRequestStrategy:
    __slots__ = (
        "_responses",
        "_request_sender",
        "_request",
        "_response_classifier",
        "_deadline",
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
        attempts_count: int,
        delays_provider: Callable[[int], float],
    ):
        self._attempts_count = attempts_count
        self._deadline = deadline
        self._request = request
        self._request_sender = request_sender
        self._responses: List[ClosableResponse] = []
        self._response_classifier = response_classifier
        self._delays_provider = delays_provider

    async def __aenter__(self) -> Response:
        pending_tasks: Set[Future[ClosableResponse]] = set()
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
        while self._responses:
            response = self._responses.pop()
            with suppress(Exception):
                await response.close()
        return False

    async def _schedule_request(self, attempt: int) -> ClosableResponse:
        await asyncio.sleep(min(self._delays_provider(attempt), self._deadline.timeout))
        if self._deadline.expired:
            return EmptyResponse(status=408)
        return await self._request_sender.send(self._request, self._deadline)
