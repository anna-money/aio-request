import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from queue import Queue
from typing import Union, List, Optional, AsyncContextManager, AsyncIterator

from aio_request import RequestSender, Request, Deadline, ClosableResponse, EmptyResponse, RequestStrategy, Response

logging.basicConfig(level="DEBUG")


@dataclass(frozen=True)
class TestResponseConfiguration:
    status: int
    delay_seconds: float


class TestRequestSender(RequestSender):
    __slots__ = ("_responses",)

    def __init__(self, responses: List[Union[int, TestResponseConfiguration]]):
        self._responses = Queue()
        for response in responses:
            self._responses.put(response)

    async def send(self, request: Request, deadline: Deadline) -> ClosableResponse:
        if self._responses.empty():
            raise RuntimeError("No response left")

        response_or_configuration = self._responses.get_nowait()
        if isinstance(response_or_configuration, TestResponseConfiguration):
            delay_seconds = response_or_configuration.delay_seconds
            if delay_seconds >= deadline.timeout:
                status = 408
                delay_seconds = deadline.timeout
            else:
                status = response_or_configuration.status
            await asyncio.sleep(delay_seconds)
        else:
            status = response_or_configuration

        return EmptyResponse(status=status)


class AlwaysSucceedRequestStrategy(RequestStrategy):
    __slots__ = ()

    def request(
        self, request: Request, deadline: Optional[Union[float, Deadline]] = None
    ) -> AsyncContextManager[Response]:
        return self._request(request, deadline)

    @asynccontextmanager
    async def _request(self, request: Request, deadline: Optional[Union[float, Deadline]]) -> AsyncIterator[Response]:
        yield EmptyResponse(status=200)


class HangedRequestStrategy(RequestStrategy):
    __slots__ = ()

    def request(
        self, request: Request, deadline: Optional[Union[float, Deadline]] = None
    ) -> AsyncContextManager[Response]:
        return self._request(request, deadline)

    @asynccontextmanager
    async def _request(self, request: Request, deadline: Optional[Union[float, Deadline]]) -> AsyncIterator[Response]:
        future = asyncio.get_event_loop().create_future()
        await future
        yield EmptyResponse(status=499)
