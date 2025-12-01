import asyncio
import contextlib
import logging
import socket
import struct
import time
import unittest.mock
from collections.abc import AsyncIterator, Callable, Generator
from typing import Protocol

import aiohttp
import aiohttp.web
import aiohttp.web_request
import aiohttp.web_response
import httpx
import pytest
import yarl
from _pytest.fixtures import SubRequest
from aiohttp.test_utils import TestClient
from pytest_aiohttp.plugin import AiohttpClient

import aio_request

logging.basicConfig(level="DEBUG")


class MockPerfCounter:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


@pytest.fixture
def mock_perf_counter() -> Generator[MockPerfCounter, None, None]:
    counter = MockPerfCounter()
    with unittest.mock.patch("aio_request.percentile_based_request_attempt_delays_provider.perf_counter", counter):
        yield counter


class ClientFactory(Protocol):
    def __call__(self, emit_system_headers: bool = True) -> aio_request.Client: ...


class FakeTransport(aio_request.Transport):
    __slots__ = ("_responses",)

    def __init__(self, *responses: int | tuple[int, float]) -> None:
        self._responses = list(reversed(responses))

    async def send(
        self, endpoint: yarl.URL, request: aio_request.Request, timeout: float
    ) -> aio_request.ClosableResponse:
        if not self._responses:
            raise RuntimeError("No response left")

        started_at = time.perf_counter()

        response = self._responses.pop()
        if isinstance(response, tuple):
            status, delay_seconds = response
            if delay_seconds >= timeout:
                status = 408
                delay_seconds = timeout
            await asyncio.sleep(delay_seconds)
        else:
            status = response

        return aio_request.EmptyResponse(elapsed=time.perf_counter() - started_at, status=status)


@pytest.fixture
async def server(aiohttp_client: AiohttpClient) -> TestClient:
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
async def client(server: TestClient) -> AsyncIterator[ClientFactory]:
    async with aiohttp.ClientSession() as client_session:

        def go(emit_system_headers: bool = True) -> aio_request.Client:
            return aio_request.setup(
                transport=aio_request.AioHttpTransport(client_session),
                endpoint=f"http://{server.server.host}:{server.server.port}/",
                emit_system_headers=emit_system_headers,
            )

        yield go


@pytest.fixture(scope="session")
def unused_port() -> Callable[[], int]:
    def f() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    return f


@pytest.fixture(params=("aiohttp", "httpx"))
async def transport(request: SubRequest) -> AsyncIterator[aio_request.Transport]:
    if request.param == "aiohttp":
        async with aiohttp.ClientSession() as client_session:
            yield aio_request.AioHttpTransport(client_session)
    elif request.param == "httpx":
        async with httpx.AsyncClient() as async_client:
            yield aio_request.HttpxTransport(async_client)
    else:
        raise ValueError(f"Unknown transport {request.param}")


@pytest.fixture
async def resetting_server_factory() -> AsyncIterator[Callable[[int], contextlib.AbstractAsyncContextManager[None]]]:
    @contextlib.asynccontextmanager
    async def run_server(port: int) -> AsyncIterator[None]:
        async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            try:
                await reader.read(1)
                sock = writer.get_extra_info("socket")
                assert sock
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            finally:
                writer.close()

        server_handle = await asyncio.start_server(handle, "127.0.0.1", port)

        yield

        server_handle.close()
        await server_handle.wait_closed()

    yield run_server
