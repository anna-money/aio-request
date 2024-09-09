import abc
import asyncio
import collections.abc
import contextlib
from typing import Generic, TypeVar

import yarl

from .base import ClosableResponse, Request, Response
from .deadline import Deadline
from .delays_provider import DelaysProvider, linear_backoff_delays
from .priority import Priority
from .response_classifier import ResponseVerdict
from .utils import Closable, cancel_futures, close, close_futures, close_single

TResponse = TypeVar("TResponse")


class ResponseWithVerdict(Generic[TResponse], Closable):
    __slots__ = ("response", "verdict")

    def __init__(self, response: TResponse, verdict: ResponseVerdict):
        self.response = response
        self.verdict = verdict

    async def close(self) -> None:
        if isinstance(self.response, Closable):
            await self.response.close()


SendRequestFunc = collections.abc.Callable[
    [yarl.URL, Request, Deadline, Priority], collections.abc.Awaitable[ResponseWithVerdict[ClosableResponse]]
]


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
    ) -> contextlib.AbstractAsyncContextManager[ResponseWithVerdict[Response]]: ...


class MethodBasedStrategy(RequestStrategy):
    __slots__ = ("__strategy_by_method",)

    def __init__(self, strategy_by_method: dict[str, RequestStrategy]):
        self.__strategy_by_method = strategy_by_method

    def request(
        self,
        send_request: SendRequestFunc,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> contextlib.AbstractAsyncContextManager[ResponseWithVerdict[Response]]:
        return self.__strategy_by_method[request.method].request(send_request, endpoint, request, deadline, priority)


def single_attempt_strategy() -> RequestStrategy:
    return SingleAttemptRequestStrategy()


def sequential_strategy(
    *, attempts_count: int = 3, delays_provider: DelaysProvider = linear_backoff_delays()
) -> RequestStrategy:
    return SequentialRequestStrategy(attempts_count=attempts_count, delays_provider=delays_provider)


def parallel_strategy(
    *, attempts_count: int = 3, delays_provider: DelaysProvider = linear_backoff_delays()
) -> RequestStrategy:
    return ParallelRequestStrategy(attempts_count=attempts_count, delays_provider=delays_provider)


def retry_until_deadline_expired(
    strategy: RequestStrategy, *, delays_provider: DelaysProvider = linear_backoff_delays()
) -> RequestStrategy:
    return RetryUntilDeadlineExpiredStrategy(strategy, delays_provider)


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
    ) -> collections.abc.AsyncIterator[ResponseWithVerdict[Response]]:
        send_result: ResponseWithVerdict[ClosableResponse] | None = None
        try:
            send_result = await send_request(endpoint, request, deadline, priority)
            yield ResponseWithVerdict[Response](send_result.response, send_result.verdict)
        finally:
            if send_result is not None:
                await asyncio.shield(close_single(send_result))

    def __repr__(self) -> str:
        return "<SingleAttemptRequestStrategy>"


class SequentialRequestStrategy(RequestStrategy):
    __slots__ = (
        "__attempts_count",
        "__delays_provider",
    )

    def __init__(
        self,
        *,
        attempts_count: int,
        delays_provider: DelaysProvider,
    ):
        if attempts_count < 1:
            raise RuntimeError("Attempts count should be >= 1")

        self.__delays_provider = delays_provider
        self.__attempts_count = attempts_count

    @contextlib.asynccontextmanager
    async def request(
        self,
        send_request: SendRequestFunc,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> collections.abc.AsyncIterator[ResponseWithVerdict[Response]]:
        responses: list[ResponseWithVerdict[ClosableResponse]] = []
        try:
            for attempt in range(self.__attempts_count):
                response = await send_request(endpoint, request, deadline, priority)
                responses.append(response)
                if response.verdict == ResponseVerdict.ACCEPT:
                    break
                if attempt + 1 == self.__attempts_count:
                    break
                retry_delay = self.__delays_provider(attempt + 1)
                if deadline.timeout < retry_delay:
                    break
                await asyncio.sleep(retry_delay)
            final_response = responses[-1]
            yield ResponseWithVerdict[Response](final_response.response, final_response.verdict)
        finally:
            await asyncio.shield(close(responses))

    def __repr__(self) -> str:
        return f"<SequentialRequestStrategy [{self.__attempts_count}]>"


class ParallelRequestStrategy(RequestStrategy):
    __slots__ = (
        "__attempts_count",
        "__delays_provider",
    )

    def __init__(
        self,
        *,
        attempts_count: int,
        delays_provider: DelaysProvider,
    ):
        if attempts_count < 1:
            raise RuntimeError("Attempts count should be >= 1")

        self.__delays_provider = delays_provider
        self.__attempts_count = attempts_count

    @contextlib.asynccontextmanager
    async def request(
        self,
        send_request: SendRequestFunc,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> collections.abc.AsyncIterator[ResponseWithVerdict[Response]]:
        completed_tasks: set[asyncio.Future[ResponseWithVerdict[ClosableResponse]]] = set()
        pending_tasks: set[asyncio.Future[ResponseWithVerdict[ClosableResponse]]] = set()
        for attempt in range(0, self.__attempts_count):
            schedule_request = self._schedule_request(attempt, send_request, endpoint, request, deadline, priority)
            pending_tasks.add(asyncio.create_task(schedule_request))

        accepted_responses: list[ResponseWithVerdict[ClosableResponse]] = []
        not_accepted_responses: list[ResponseWithVerdict[ClosableResponse]] = []
        try:
            try:
                while pending_tasks:
                    completed_tasks, pending_tasks = await asyncio.wait(
                        pending_tasks, return_when=asyncio.FIRST_COMPLETED
                    )
                    while completed_tasks:
                        completed_task = completed_tasks.pop()
                        response = await completed_task
                        if response.verdict == ResponseVerdict.ACCEPT:
                            accepted_responses.append(response)
                        else:
                            not_accepted_responses.append(response)
                    if accepted_responses:
                        break
            finally:
                await asyncio.shield(cancel_futures(pending_tasks))

            final_response = accepted_responses[0] if accepted_responses else not_accepted_responses[0]
            yield ResponseWithVerdict[Response](final_response.response, final_response.verdict)
        finally:
            await asyncio.shield(
                asyncio.gather(
                    close_futures(pending_tasks | completed_tasks, lambda x: x.response),
                    close(accepted_responses + not_accepted_responses),
                    return_exceptions=True,
                )
            )

    async def _schedule_request(
        self,
        attempt: int,
        send_request: SendRequestFunc,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ResponseWithVerdict[ClosableResponse]:
        if attempt > 0:
            await asyncio.sleep(min(self.__delays_provider(attempt), deadline.timeout))
        return await send_request(endpoint, request, deadline, priority)

    def __repr__(self) -> str:
        return f"<ParallelRequestStrategy [{self.__attempts_count}]>"


class RetryUntilDeadlineExpiredStrategy(RequestStrategy):
    __slots__ = ("__base_strategy", "__delays_provider")

    def __init__(self, base_strategy: RequestStrategy, delays_provider: DelaysProvider):
        self.__delays_provider = delays_provider
        self.__base_strategy = base_strategy

    @contextlib.asynccontextmanager
    async def request(
        self,
        send_request: SendRequestFunc,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> collections.abc.AsyncIterator[ResponseWithVerdict[Response]]:
        attempt = 0
        while True:
            response_ctx = self.__base_strategy.request(send_request, endpoint, request, deadline, priority)
            async with response_ctx as response:
                if response.verdict == ResponseVerdict.ACCEPT or deadline.expired:
                    yield response
                    return

            attempt += 1
            await asyncio.sleep(min(self.__delays_provider(attempt), deadline.timeout))

    def __repr__(self) -> str:
        return "<RetryUntilDeadlineExpiredStrategy>"
