import asyncio
import logging
from dataclasses import dataclass
from queue import Queue
from typing import List, Union

from aio_request import ClosableResponse, Deadline, EmptyResponse, Priority, Request, RequestSender

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

    async def send(self, request: Request, deadline: Deadline, priority: Priority) -> ClosableResponse:
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
