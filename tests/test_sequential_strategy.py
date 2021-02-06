from aio_request import Deadline, DefaultResponseClassifier, RequestStrategiesFactory, get, linear_delays
from tests.conftest import TestRequestSender, TestResponseConfiguration


async def test_timeout_because_of_expiration():
    strategies_factory = RequestStrategiesFactory(
        request_sender=TestRequestSender([TestResponseConfiguration(status=200, delay_seconds=5)]),
        response_classifier=DefaultResponseClassifier(),
    )
    sequential_strategy = strategies_factory.sequential(attempts_count=3, delays_provider=linear_delays())
    deadline = Deadline.from_timeout(1)
    async with sequential_strategy.request(get("hello"), deadline=deadline) as response:
        assert response.status == 408
        assert deadline.expired


async def test_succeed_response_received():
    strategies_factory = RequestStrategiesFactory(TestRequestSender([489, 200]))
    sequential_strategy = strategies_factory.sequential()
    deadline = Deadline.from_timeout(1)
    async with sequential_strategy.request(get("hello"), deadline=deadline) as response:
        assert response.status == 200
        assert not deadline.expired


async def test_succeed_response_not_received_too_many_failures():
    strategies_factory = RequestStrategiesFactory(TestRequestSender([499, 499, 499]))
    sequential_strategy = strategies_factory.sequential()
    deadline = Deadline.from_timeout(1)
    async with sequential_strategy.request(get("hello"), deadline=deadline) as response:
        assert response.status == 499
        assert not deadline.expired
