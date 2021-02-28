import abc
import asyncio
import contextlib
from typing import AsyncContextManager, AsyncIterator, Callable, Dict, List, Set, Union

import yarl

from .base import ClosableResponse, Request, Response
from .deadline import Deadline
from .delays_provider import linear_delays
from .priority import Priority
from .request_sender import RequestSender
from .response_classifier import ResponseClassifier, ResponseVerdict
from .utils import cancel_futures, close, close_futures


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
        "_endpoint",
        "_response_classifier",
    )

    def __init__(
        self,
        request_sender: RequestSender,
        endpoint: Union[str, yarl.URL],
        response_classifier: ResponseClassifier,
    ):
        self._request_sender = request_sender
        self._endpoint = yarl.URL(endpoint) if isinstance(endpoint, str) else endpoint
        self._response_classifier = response_classifier

    def sequential(
        self, *, attempts_count: int = 3, delays_provider: Callable[[int], float] = linear_delays()
    ) -> RequestStrategy:
        return SequentialRequestStrategy(
            request_sender=self._request_sender,
            endpoint=self._endpoint,
            response_classifier=self._response_classifier,
            attempts_count=attempts_count,
            delays_provider=delays_provider,
        )

    def parallel(
        self, *, attempts_count: int = 3, delays_provider: Callable[[int], float] = linear_delays()
    ) -> RequestStrategy:
        return ParallelRequestStrategy(
            request_sender=self._request_sender,
            endpoint=self._endpoint,
            response_classifier=self._response_classifier,
            attempts_count=attempts_count,
            delays_provider=delays_provider,
        )


class SequentialRequestStrategy(RequestStrategy):
    __slots__ = (
        "_endpoint",
        "_request_sender",
        "_response_classifier",
        "_attempts_count",
        "_delays_provider",
    )

    def __init__(
        self,
        *,
        request_sender: RequestSender,
        endpoint: yarl.URL,
        response_classifier: ResponseClassifier,
        attempts_count: int,
        delays_provider: Callable[[int], float],
    ):
        if attempts_count < 1:
            raise RuntimeError("Attempts count should be >= 1")

        self._endpoint = endpoint
        self._request_sender = request_sender
        self._response_classifier = response_classifier
        self._delays_provider = delays_provider
        self._attempts_count = attempts_count

    @contextlib.asynccontextmanager
    async def request(
        self, request: Request, deadline: Deadline, priority: Priority = Priority.NORMAL
    ) -> AsyncIterator[Response]:
        responses: List[ClosableResponse] = []
        try:
            for attempt in range(self._attempts_count):
                response = await self._request_sender.send(self._endpoint, request, deadline, priority)
                responses.append(response)
                if self._response_classifier.classify(response) == ResponseVerdict.ACCEPT:
                    break
                if attempt + 1 == self._attempts_count:
                    break
                retry_delay = self._delays_provider(attempt + 1)
                if deadline.timeout < retry_delay:
                    break
                await asyncio.sleep(retry_delay)
            yield responses[-1]
        finally:
            await asyncio.shield(close(responses))


class ParallelRequestStrategy(RequestStrategy):
    __slots__ = (
        "_endpoint",
        "_request_sender",
        "_response_classifier",
        "_attempts_count",
        "_delays_provider",
    )

    def __init__(
        self,
        *,
        request_sender: RequestSender,
        endpoint: yarl.URL,
        response_classifier: ResponseClassifier,
        attempts_count: int,
        delays_provider: Callable[[int], float],
    ):
        if attempts_count < 1:
            raise RuntimeError("Attempts count should be >= 1")

        self._endpoint = endpoint
        self._request_sender = request_sender
        self._response_classifier = response_classifier
        self._delays_provider = delays_provider
        self._attempts_count = attempts_count

    async def _schedule_request(
        self, attempt: int, request: Request, deadline: Deadline, priority: Priority = Priority.NORMAL
    ) -> ClosableResponse:
        if attempt > 0:
            await asyncio.sleep(min(self._delays_provider(attempt), deadline.timeout))
        return await self._request_sender.send(self._endpoint, request, deadline, priority)

    @contextlib.asynccontextmanager
    async def request(
        self, request: Request, deadline: Deadline, priority: Priority = Priority.NORMAL
    ) -> AsyncIterator[Response]:
        completed_tasks: Set[asyncio.Future[ClosableResponse]] = set()
        pending_tasks: Set[asyncio.Future[ClosableResponse]] = set()
        for attempt in range(0, self._attempts_count):
            pending_tasks.add(asyncio.create_task(self._schedule_request(attempt, request, deadline, priority)))

        accepted_responses: List[ClosableResponse] = []
        not_accepted_responses: List[ClosableResponse] = []
        try:
            try:
                while pending_tasks:
                    completed_tasks, pending_tasks = await asyncio.wait(
                        pending_tasks, return_when=asyncio.FIRST_COMPLETED
                    )
                    while completed_tasks:
                        completed_task = completed_tasks.pop()
                        response = await completed_task
                        if self._response_classifier.classify(response) == ResponseVerdict.ACCEPT:
                            accepted_responses.append(response)
                        else:
                            not_accepted_responses.append(response)
                    if accepted_responses:
                        break
            finally:
                await asyncio.shield(cancel_futures(pending_tasks))

            yield accepted_responses[0] if accepted_responses else not_accepted_responses[0]
        finally:
            await asyncio.shield(close_futures(pending_tasks | completed_tasks))
            await asyncio.shield(close(accepted_responses + not_accepted_responses))
