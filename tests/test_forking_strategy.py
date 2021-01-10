from aio_request import RequestStrategiesFactory, DefaultResponseClassifier, linear_delays, get, Deadline
from tests.conftest import TestRequestSender, TestResponseConfiguration


async def test_timeout_because_of_expiration():
    strategies_factory = RequestStrategiesFactory(
        TestRequestSender(
            [
                TestResponseConfiguration(code=200, delay_seconds=5),
                TestResponseConfiguration(code=200, delay_seconds=5),
                TestResponseConfiguration(code=200, delay_seconds=5),
            ],
        )
    )
    forking_strategy = strategies_factory.forking()
    deadline = Deadline.after(seconds=1)
    async with forking_strategy.request(get("hello"), deadline=deadline) as response:
        assert response.code == 408
        assert deadline.expired


async def test_succeed_response_received_first_slow_request():
    strategies_factory = RequestStrategiesFactory(
        TestRequestSender([TestResponseConfiguration(code=200, delay_seconds=5), 200])
    )
    forking_strategy = strategies_factory.forking()
    deadline = Deadline.after(seconds=1)
    async with forking_strategy.request(get("hello"), deadline=deadline) as response:
        assert response.code == 200
        assert not deadline.expired


async def test_succeed_response_received():
    strategies_factory = RequestStrategiesFactory(
        request_sender=TestRequestSender([499, 200]), response_classifier=DefaultResponseClassifier(),
    )
    forking_strategy = strategies_factory.forking()
    deadline = Deadline.after(seconds=1)
    async with forking_strategy.request(get("hello"), deadline=deadline) as response:
        assert response.code == 200
        assert not deadline.expired


async def test_succeed_response_not_received_too_many_failures():
    strategies_factory = RequestStrategiesFactory(
        request_sender=TestRequestSender([499, 499, 499]), response_classifier=DefaultResponseClassifier(),
    )
    forking_strategy = strategies_factory.forking(attempts_count=3, delays_provider=linear_delays())
    deadline = Deadline.after(seconds=1)
    async with forking_strategy.request(get("hello"), deadline=deadline) as response:
        assert response.code == 499
        assert not deadline.expired
