import aio_request

from .conftest import FakeTransport


async def test_timeout_because_of_expiration() -> None:
    client = aio_request.setup(
        transport=FakeTransport(500, 500, 500, 500, 500, 500, 500),
        endpoint="http://service.com",
    )
    deadline = aio_request.Deadline.from_timeout(1)

    response_ctx = client.request(
        aio_request.get("hello"),
        deadline=deadline,
        strategy=aio_request.retry_until_deadline_expired(aio_request.single_attempt_strategy()),
    )
    async with response_ctx as response:
        assert response.status == 408
        assert deadline.expired


async def test_success_from_first_attempt() -> None:
    client = aio_request.setup(
        transport=FakeTransport(200),
        endpoint="http://service.com",
    )
    deadline = aio_request.Deadline.from_timeout(1)

    response_ctx = client.request(
        aio_request.get("hello"),
        deadline=deadline,
        strategy=aio_request.retry_until_deadline_expired(aio_request.single_attempt_strategy()),
    )
    async with response_ctx as response:
        assert response.status == 200
        assert not deadline.expired


async def test_success_from_second_attempt() -> None:
    client = aio_request.setup(
        transport=FakeTransport(500, 200),
        endpoint="http://service.com",
    )
    deadline = aio_request.Deadline.from_timeout(1)

    response_ctx = client.request(
        aio_request.get("hello"),
        deadline=deadline,
        strategy=aio_request.retry_until_deadline_expired(aio_request.single_attempt_strategy()),
    )
    async with response_ctx as response:
        assert response.status == 200
        assert not deadline.expired
