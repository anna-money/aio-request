import asyncio
import logging
from dataclasses import dataclass
from queue import Queue
from typing import Union, List

from aio_request import RequestSender, Request, Deadline, ClosableResponse
from aio_request.utils import empty_close, EMPTY_HEADERS

logging.basicConfig(level="DEBUG")


@dataclass(frozen=True)
class TestResponseConfiguration:
    __slots__ = ("code", "delay_seconds")

    code: int
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
                code = 408
                delay_seconds = deadline.timeout
            else:
                code = response_or_configuration.code
            await asyncio.sleep(delay_seconds)
        else:
            code = response_or_configuration

        return ClosableResponse(code, EMPTY_HEADERS, bytes(), empty_close)
