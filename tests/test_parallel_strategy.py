import aio_request

from .conftest import FakeTransport


async def test_timeout_due_to_low_timeout() -> None:
    client = aio_request.setup(
        transport=FakeTransport(200),
        endpoint="http://service.com",
        low_timeout_threshold=0.02,
    )
    deadline = aio_request.Deadline.from_timeout(0.01)
    response_ctx = client.request(
        aio_request.get("hello"),
        deadline=deadline,
        strategy=aio_request.parallel_strategy(),
    )
    async with response_ctx as response:
        assert response.status == 408
        assert aio_request.Header.X_DO_NOT_RETRY in response.headers


async def test_timeout_due_to_expiration() -> None:
    client = aio_request.setup(
        transport=FakeTransport(
            (200, 5),
            (200, 5),
            (200, 5),
        ),
        endpoint="http://service.com",
    )

    deadline = aio_request.Deadline.from_timeout(1)
    response_ctx = client.request(aio_request.get("hello"), deadline=deadline, strategy=aio_request.parallel_strategy())
    async with response_ctx as response:
        assert response.status == 408
        assert deadline.expired


async def test_succeed_response_received_first_slow_request() -> None:
    client = aio_request.setup(
        transport=FakeTransport((200, 5), 200),
        endpoint="http://service.com",
    )
    deadline = aio_request.Deadline.from_timeout(1)
    response_ctx = client.request(aio_request.get("hello"), deadline=deadline, strategy=aio_request.parallel_strategy())
    async with response_ctx as response:
        assert response.status == 200
        assert not deadline.expired


async def test_succeed_response_received() -> None:
    client = aio_request.setup(transport=FakeTransport(489, 200), endpoint="http://service.com")
    deadline = aio_request.Deadline.from_timeout(1)
    response_ctx = client.request(aio_request.get("hello"), deadline=deadline, strategy=aio_request.parallel_strategy())
    async with response_ctx as response:
        assert response.status == 200
        assert not deadline.expired


async def test_succeed_response_not_received_too_many_failures() -> None:
    client = aio_request.setup(transport=FakeTransport(499, 499, 499), endpoint="http://service.com")
    deadline = aio_request.Deadline.from_timeout(1)
    response_ctx = client.request(
        aio_request.get("hello"),
        deadline=deadline,
        strategy=aio_request.parallel_strategy(attempts_count=3, delays_provider=aio_request.linear_backoff_delays()),
    )
    async with response_ctx as response:
        assert response.status == 499
        assert not deadline.expired
