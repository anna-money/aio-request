import asyncio
import contextlib

from aio_request import (
    Deadline,
    DefaultResponseClassifier,
    Priority,
    RequestSender,
    RequestStrategiesFactory,
    get,
    linear_delays,
)
from tests.conftest import FakeResponseConfiguration, FakeTransport


async def test_timeout_because_of_expiration():
    strategies_factory = RequestStrategiesFactory(
        request_sender=RequestSender(
            transport=FakeTransport([FakeResponseConfiguration(status=200, delay_seconds=5)]),
        ),
        endpoint="http://service.com",
        response_classifier=DefaultResponseClassifier(),
    )
    sequential_strategy = strategies_factory.sequential(attempts_count=3, delays_provider=linear_delays())
    deadline = Deadline.from_timeout(1)
    async with sequential_strategy.request(get("hello"), deadline=deadline) as response:
        assert response.status == 408
        assert deadline.expired


async def test_succeed_response_received():
    strategies_factory = RequestStrategiesFactory(
        request_sender=RequestSender(
            transport=FakeTransport([489, 200]),
        ),
        endpoint="http://service.com",
        response_classifier=DefaultResponseClassifier(),
    )
    sequential_strategy = strategies_factory.sequential()
    deadline = Deadline.from_timeout(1)
    async with sequential_strategy.request(get("hello"), deadline=deadline, priority=Priority.NORMAL) as response:
        assert response.status == 200
        assert not deadline.expired


async def test_succeed_response_not_received_too_many_failures():
    strategies_factory = RequestStrategiesFactory(
        request_sender=RequestSender(transport=FakeTransport([499, 499, 499])),
        endpoint="http://service.com",
        response_classifier=DefaultResponseClassifier(),
    )
    sequential_strategy = strategies_factory.sequential()
    deadline = Deadline.from_timeout(1)
    async with sequential_strategy.request(get("hello"), deadline=deadline) as response:
        assert response.status == 499
        assert not deadline.expired


async def test_cancellation():
    async def send_request():
        strategies_factory = RequestStrategiesFactory(
            request_sender=RequestSender(
                transport=FakeTransport([489, FakeResponseConfiguration(status=200, delay_seconds=100)]),
            ),
            endpoint="http://service.com",
            response_classifier=DefaultResponseClassifier(),
        )
        sequential_strategy = strategies_factory.sequential(attempts_count=3, delays_provider=linear_delays())
        deadline = Deadline.from_timeout(500)
        async with sequential_strategy.request(get("hello"), deadline=deadline):
            raise RuntimeError("Should not be here")

    send_request_task = asyncio.create_task(send_request())
    await asyncio.sleep(1)
    send_request_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await send_request_task
