import asyncio
import contextlib

from prometheus_client import Histogram, Counter

from aio_request import get
from aio_request.prometheus import PrometheusAwareStrategy
from tests.conftest import AlwaysSucceedRequestStrategy, HangedRequestStrategy

requests_latency_histogram = Histogram(
    name="requests_latency", documentation="Requests latency", labelnames=("service", "method"),
)
requests_counter = Counter(name="requests", documentation="Requests", labelnames=("service", "method", "status"))


async def test_success_request():
    strategy = PrometheusAwareStrategy(
        AlwaysSucceedRequestStrategy(), "service", requests_latency_histogram, requests_counter
    )
    async with strategy.request(get("/")) as response:
        assert response.status == 200


async def test_cancelled_request():
    strategy = PrometheusAwareStrategy(HangedRequestStrategy(), "service", requests_latency_histogram, requests_counter)

    async def make_request(s):
        async with s.request(get("/")):
            assert True, "Should not be here"

    request_task = asyncio.create_task(make_request(strategy))
    await asyncio.sleep(1)
    request_task.cancel()

    with contextlib.suppress(asyncio.CancelledError):
        await request_task


async def test_cancelled_request_processing():
    strategy = PrometheusAwareStrategy(
        AlwaysSucceedRequestStrategy(), "service", requests_latency_histogram, requests_counter
    )

    async def make_request(s):
        async with s.request(get("/")):
            future = asyncio.get_event_loop().create_future()
            await future

    request_task = asyncio.create_task(make_request(strategy))
    await asyncio.sleep(1)
    request_task.cancel()

    with contextlib.suppress(asyncio.CancelledError):
        await request_task
