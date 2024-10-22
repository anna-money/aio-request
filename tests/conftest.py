import asyncio
import dataclasses
import logging
import queue

import aiohttp.web
import aiohttp.web_request
import aiohttp.web_response
import pytest
import yarl

import aio_request

logging.basicConfig(level="DEBUG")


@dataclasses.dataclass(frozen=True)
class FakeResponseConfiguration:
    status: int
    delay_seconds: float = 0


class FakeTransport(aio_request.Transport):
    __slots__ = ("_responses",)

    def __init__(self, responses: list[int | FakeResponseConfiguration]):
        self._responses = queue.Queue()
        for response in responses:
            self._responses.put(response)

    async def send(
        self, endpoint: yarl.URL, request: aio_request.Request, timeout: float
    ) -> aio_request.ClosableResponse:
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

        return aio_request.EmptyResponse(status=status)


@pytest.fixture
async def server(aiohttp_client):
    async def handler(request: aiohttp.web_request.Request) -> aiohttp.web_response.Response:
        await asyncio.sleep(float(request.query.get("delay", "0")))
        return aiohttp.web_response.Response()

    @aio_request.aiohttp_timeout(seconds=0.2)
    async def handler_with_timeout(request: aiohttp.web_request.Request) -> aiohttp.web_response.Response:
        await asyncio.sleep(float(request.query.get("delay", "0")))
        return aiohttp.web_response.Response()

    class ViewWithTimeout(aiohttp.web.View):
        @aio_request.aiohttp_timeout(seconds=0.2)
        async def get(self) -> aiohttp.web.StreamResponse:
            await asyncio.sleep(float(self.request.query.get("delay", "0")))
            return aiohttp.web_response.Response()

    app = aiohttp.web.Application(
        middlewares=[aio_request.aiohttp_middleware_factory(cancel_on_timeout=True)],
    )
    app.router.add_get("/", handler)
    app.router.add_get("/with_timeout", handler_with_timeout)
    app.router.add_get("/view_with_timeout", ViewWithTimeout)
    return await aiohttp_client(app)


@pytest.fixture
async def client(server):
    async with aiohttp.ClientSession() as client_session:

        def go(emit_system_headers: bool = True):
            return aio_request.setup_v2(
                transport=aio_request.AioHttpTransport(client_session),
                endpoint=f"http://{server.server.host}:{server.server.port}/",
                emit_system_headers=emit_system_headers,
                circuit_breaker=aio_request.NoopCircuitBreaker[yarl.URL, aio_request.ClosableResponse](),
            )

        yield go
