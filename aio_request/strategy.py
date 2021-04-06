import abc
import asyncio
import contextlib
from typing import AsyncContextManager, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Set

import yarl

from .base import ClosableResponse, Request, Response
from .deadline import Deadline
from .delays_provider import linear_delays
from .priority import Priority
from .response_classifier import ResponseVerdict
from .utils import cancel_futures, close, close_futures, close_single


class SendRequestResult:
    __slots__ = ("response", "verdict")

    def __init__(self, response: ClosableResponse, verdict: ResponseVerdict):
        self.response = response
        self.verdict = verdict


SendRequestFunc = Callable[[yarl.URL, Request, Deadline, Priority], Awaitable[SendRequestResult]]


class RequestStrategy(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def request(
        self,
        send_request: SendRequestFunc,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> AsyncContextManager[Response]:
        ...


class MethodBasedStrategy(RequestStrategy):
    __slots__ = ("_strategy_by_method",)

    def __init__(self, strategy_by_method: Dict[str, RequestStrategy]):
        self._strategy_by_method = strategy_by_method

    def request(
        self,
        send_request: SendRequestFunc,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> AsyncContextManager[Response]:
        return self._strategy_by_method[request.method].request(send_request, endpoint, request, deadline, priority)


def single_attempt_strategy() -> RequestStrategy:
    return SingleAttemptRequestStrategy()


def sequential_strategy(
    *, attempts_count: int = 3, delays_provider: Callable[[int], float] = linear_delays()
) -> RequestStrategy:
    return SequentialRequestStrategy(
        attempts_count=attempts_count,
        delays_provider=delays_provider,
    )


def parallel_strategy(
    *, attempts_count: int = 3, delays_provider: Callable[[int], float] = linear_delays()
) -> RequestStrategy:
    return ParallelRequestStrategy(
        attempts_count=attempts_count,
        delays_provider=delays_provider,
    )


class SingleAttemptRequestStrategy(RequestStrategy):
    __slots__ = ()

    @contextlib.asynccontextmanager
    async def request(
        self,
        send_request: SendRequestFunc,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> AsyncIterator[Response]:
        send_result: Optional[SendRequestResult] = None
        try:
            send_result = await send_request(endpoint, request, deadline, priority)
            yield send_result.response
        finally:
            if send_result is not None:
                await asyncio.shield(close_single(send_result.response))


class SequentialRequestStrategy(RequestStrategy):
    __slots__ = (
        "_attempts_count",
        "_delays_provider",
    )

    def __init__(
        self,
        *,
        attempts_count: int,
        delays_provider: Callable[[int], float],
    ):
        if attempts_count < 1:
            raise RuntimeError("Attempts count should be >= 1")

        self._delays_provider = delays_provider
        self._attempts_count = attempts_count

    @contextlib.asynccontextmanager
    async def request(
        self,
        send_request: SendRequestFunc,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> AsyncIterator[Response]:
        responses: List[ClosableResponse] = []
        try:
            for attempt in range(self._attempts_count):
                send_result = await send_request(endpoint, request, deadline, priority)
                responses.append(send_result.response)
                if send_result.verdict == ResponseVerdict.ACCEPT:
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
        "_attempts_count",
        "_delays_provider",
    )

    def __init__(
        self,
        *,
        attempts_count: int,
        delays_provider: Callable[[int], float],
    ):
        if attempts_count < 1:
            raise RuntimeError("Attempts count should be >= 1")

        self._delays_provider = delays_provider
        self._attempts_count = attempts_count

    async def _schedule_request(
        self,
        attempt: int,
        send_request: SendRequestFunc,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> SendRequestResult:
        if attempt > 0:
            await asyncio.sleep(min(self._delays_provider(attempt), deadline.timeout))
        return await send_request(endpoint, request, deadline, priority)

    @contextlib.asynccontextmanager
    async def request(
        self,
        send_request: SendRequestFunc,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> AsyncIterator[Response]:
        completed_tasks: Set[asyncio.Future[SendRequestResult]] = set()
        pending_tasks: Set[asyncio.Future[SendRequestResult]] = set()
        for attempt in range(0, self._attempts_count):
            schedule_request = self._schedule_request(attempt, send_request, endpoint, request, deadline, priority)
            pending_tasks.add(asyncio.create_task(schedule_request))

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
                        send_result = await completed_task
                        if send_result.verdict == ResponseVerdict.ACCEPT:
                            accepted_responses.append(send_result.response)
                        else:
                            not_accepted_responses.append(send_result.response)
                    if accepted_responses:
                        break
            finally:
                await asyncio.shield(cancel_futures(pending_tasks))

            yield accepted_responses[0] if accepted_responses else not_accepted_responses[0]
        finally:
            await asyncio.shield(close_futures(pending_tasks | completed_tasks, lambda x: x.response))
            await asyncio.shield(close(accepted_responses + not_accepted_responses))
