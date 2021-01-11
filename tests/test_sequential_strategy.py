from aio_request import RequestStrategiesFactory, DefaultResponseClassifier, linear_delays, get, Deadline
from tests.conftest import TestRequestSender, TestResponseConfiguration


async def test_timeout_because_of_expiration():
    strategies_factory = RequestStrategiesFactory(
        request_sender=TestRequestSender([TestResponseConfiguration(status=200, delay_seconds=5)]),
        response_classifier=DefaultResponseClassifier(),
    )
    sequential_strategy = strategies_factory.sequential(attempts_count=3, delays_provider=linear_delays())
    deadline = Deadline.after_seconds(seconds=1)
    async with sequential_strategy.request(get("hello"), deadline=deadline) as response:
        assert response.status == 408
        assert deadline.expired


async def test_succeed_response_received():
    strategies_factory = RequestStrategiesFactory(TestRequestSender([499, 200]))
    sequential_strategy = strategies_factory.sequential()
    deadline = Deadline.after_seconds(seconds=1)
    async with sequential_strategy.request(get("hello"), deadline=deadline) as response:
        assert response.status == 200
        assert not deadline.expired


async def test_succeed_response_not_received_too_many_failures():
    strategies_factory = RequestStrategiesFactory(TestRequestSender([499, 499, 499]))
    sequential_strategy = strategies_factory.sequential()
    deadline = Deadline.after_seconds(seconds=1)
    async with sequential_strategy.request(get("hello"), deadline=deadline) as response:
        assert response.status == 499
        assert not deadline.expired
