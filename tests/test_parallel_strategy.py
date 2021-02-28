from aio_request import Deadline, DefaultResponseClassifier, RequestSender, RequestStrategiesFactory, get, linear_delays
from tests.conftest import FakeResponseConfiguration, FakeTransport


async def test_timeout_because_of_expiration():
    strategies_factory = RequestStrategiesFactory(
        request_sender=RequestSender(
            FakeTransport(
                [
                    FakeResponseConfiguration(status=200, delay_seconds=5),
                    FakeResponseConfiguration(status=200, delay_seconds=5),
                    FakeResponseConfiguration(status=200, delay_seconds=5),
                ],
            )
        ),
        endpoint="http://service.com",
        response_classifier=DefaultResponseClassifier(),
    )
    parallel = strategies_factory.parallel()
    deadline = Deadline.from_timeout(1)
    async with parallel.request(get("hello"), deadline=deadline) as response:
        assert response.status == 408
        assert deadline.expired


async def test_succeed_response_received_first_slow_request():
    strategies_factory = RequestStrategiesFactory(
        request_sender=RequestSender(FakeTransport([FakeResponseConfiguration(status=200, delay_seconds=5), 200])),
        endpoint="http://service.com",
        response_classifier=DefaultResponseClassifier(),
    )
    parallel = strategies_factory.parallel()
    deadline = Deadline.from_timeout(1)
    async with parallel.request(get("hello"), deadline=deadline) as response:
        assert response.status == 200
        assert not deadline.expired


async def test_succeed_response_received():
    strategies_factory = RequestStrategiesFactory(
        request_sender=RequestSender(FakeTransport([489, 200])),
        response_classifier=DefaultResponseClassifier(),
        endpoint="http://service.com",
    )
    parallel = strategies_factory.parallel()
    deadline = Deadline.from_timeout(1)
    async with parallel.request(get("hello"), deadline=deadline) as response:
        assert response.status == 200
        assert not deadline.expired


async def test_succeed_response_not_received_too_many_failures():
    strategies_factory = RequestStrategiesFactory(
        request_sender=RequestSender(FakeTransport([499, 499, 499])),
        response_classifier=DefaultResponseClassifier(),
        endpoint="http://service.com",
    )
    parallel = strategies_factory.parallel(attempts_count=3, delays_provider=linear_delays())
    deadline = Deadline.from_timeout(1)
    async with parallel.request(get("hello"), deadline=deadline) as response:
        assert response.status == 499
        assert not deadline.expired
