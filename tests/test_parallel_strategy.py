import aio_request
from tests.conftest import FakeResponseConfiguration, FakeTransport


async def test_timeout_because_of_expiration():
    client = aio_request.setup(
        transport=FakeTransport(
            [
                FakeResponseConfiguration(status=200, delay_seconds=5),
                FakeResponseConfiguration(status=200, delay_seconds=5),
                FakeResponseConfiguration(status=200, delay_seconds=5),
            ]
        ),
        endpoint="http://service.com",
    )

    deadline = aio_request.Deadline.from_timeout(1)
    response_ctx = client.request(aio_request.get("hello"), deadline=deadline, strategy=aio_request.parallel_strategy())
    async with response_ctx as response:
        assert response.status == 408
        assert deadline.expired


async def test_succeed_response_received_first_slow_request():
    client = aio_request.setup(
        transport=FakeTransport([FakeResponseConfiguration(status=200, delay_seconds=5), 200]),
        endpoint="http://service.com",
    )
    deadline = aio_request.Deadline.from_timeout(1)
    response_ctx = client.request(aio_request.get("hello"), deadline=deadline, strategy=aio_request.parallel_strategy())
    async with response_ctx as response:
        assert response.status == 200
        assert not deadline.expired


async def test_succeed_response_received():
    client = aio_request.setup(transport=FakeTransport([489, 200]), endpoint="http://service.com")
    deadline = aio_request.Deadline.from_timeout(1)
    response_ctx = client.request(aio_request.get("hello"), deadline=deadline, strategy=aio_request.parallel_strategy())
    async with response_ctx as response:
        assert response.status == 200
        assert not deadline.expired


async def test_succeed_response_not_received_too_many_failures():
    client = aio_request.setup(transport=FakeTransport([499, 499, 499]), endpoint="http://service.com")
    deadline = aio_request.Deadline.from_timeout(1)
    response_ctx = client.request(
        aio_request.get("hello"),
        deadline=deadline,
        strategy=aio_request.parallel_strategy(attempts_count=3, delays_provider=aio_request.linear_delays()),
    )
    async with response_ctx as response:
        assert response.status == 499
        assert not deadline.expired
