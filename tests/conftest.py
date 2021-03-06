import asyncio
import logging
from dataclasses import dataclass
from queue import Queue
from typing import List, Union

import aiohttp.web
import aiohttp.web_request
import aiohttp.web_response
import pytest
import yarl

from aio_request import (
    AioHttpTransport,
    ClosableResponse,
    EmptyResponse,
    Request,
    Transport,
    aiohttp_middleware_factory,
    setup,
)

logging.basicConfig(level="DEBUG")


@dataclass(frozen=True)
class FakeResponseConfiguration:
    status: int
    delay_seconds: float


class FakeTransport(Transport):
    __slots__ = ("_responses",)

    def __init__(self, responses: List[Union[int, FakeResponseConfiguration]]):
        self._responses = Queue()
        for response in responses:
            self._responses.put(response)

    async def send(self, endpoint: yarl.URL, request: Request, timeout: float) -> ClosableResponse:
        if self._responses.empty():
            raise RuntimeError("No response left")

        response_or_configuration = self._responses.get_nowait()
        if isinstance(response_or_configuration, FakeResponseConfiguration):
            delay_seconds = response_or_configuration.delay_seconds
            if delay_seconds >= timeout:
                status = 408
                delay_seconds = timeout
            else:
                status = response_or_configuration.status
            await asyncio.sleep(delay_seconds)
        else:
            status = response_or_configuration

        return EmptyResponse(status=status)


@pytest.fixture
async def service(aiohttp_client):
    async def handler(request: aiohttp.web_request.Request) -> aiohttp.web_response.Response:
        await asyncio.sleep(float(request.query.get("delay", 0)))
        return aiohttp.web_response.Response()

    app = aiohttp.web.Application(middlewares=[aiohttp_middleware_factory()])
    app.router.add_get("/get", handler)
    app.router.add_post("/post", handler)
    return await aiohttp_client(app)


@pytest.fixture
async def client(service):
    async with aiohttp.ClientSession() as client_session:
        yield setup(
            transport=AioHttpTransport(client_session),
            endpoint=f"http://{service.server.host}:{service.server.port}/",
        )
