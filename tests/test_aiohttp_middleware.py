import aio_request
from tests.conftest import ClientFactory


async def test_success(client: ClientFactory) -> None:
    response_ctx = client().request(
        aio_request.get("?delay=1"),
        deadline=aio_request.Deadline.from_timeout(1.5),
        strategy=aio_request.single_attempt_strategy(),
    )
    async with response_ctx as response:
        assert response.status == 200


async def test_not_enough_timeout(client: ClientFactory) -> None:
    response_ctx = client().request(
        aio_request.get("?delay=1"),
        deadline=aio_request.Deadline.from_timeout(0.5),
        strategy=aio_request.single_attempt_strategy(),
    )
    async with response_ctx as response:
        assert response.status == 408


async def test_expired_budget(client: ClientFactory) -> None:
    response_ctx = client().request(
        aio_request.get("?delay=1"),
        deadline=aio_request.Deadline.from_timeout(0),
        strategy=aio_request.single_attempt_strategy(),
    )
    async with response_ctx as response:
        assert response.status == 408


async def test_low_timeout_threshold(client: ClientFactory) -> None:
    response_ctx = client().request(
        aio_request.get("?delay=1"),
        deadline=aio_request.Deadline.from_timeout(0.005),
        strategy=aio_request.single_attempt_strategy(),
    )
    async with response_ctx as response:
        assert response.status == 408


async def test_func_handler_timeout(client: ClientFactory) -> None:
    deadline = aio_request.Deadline.from_timeout(1)
    response_ctx = client(emit_system_headers=False).request(
        aio_request.get("with_timeout?delay=1"),
        deadline=deadline,
        strategy=aio_request.single_attempt_strategy(),
    )
    async with response_ctx as response:
        assert response.status == 408
        assert not deadline.expired


async def test_view_handler_timeout(client: ClientFactory) -> None:
    deadline = aio_request.Deadline.from_timeout(1)
    response_ctx = client(emit_system_headers=False).request(
        aio_request.get("view_with_timeout?delay=1"),
        deadline=deadline,
        strategy=aio_request.single_attempt_strategy(),
    )
    async with response_ctx as response:
        assert response.status == 408
        assert not deadline.expired


async def test_func_handler_timeout_priority(client: ClientFactory) -> None:
    deadline = aio_request.Deadline.from_timeout(1)
    response_ctx = client().request(
        aio_request.get("with_timeout?delay=0.5"),
        deadline=deadline,
        strategy=aio_request.single_attempt_strategy(),
    )
    async with response_ctx as response:
        assert response.status == 200
        assert not deadline.expired


async def test_view_handler_timeout_priority(client: ClientFactory) -> None:
    deadline = aio_request.Deadline.from_timeout(1)
    response_ctx = client().request(
        aio_request.get("view_with_timeout?delay=0.5"),
        deadline=deadline,
        strategy=aio_request.single_attempt_strategy(),
    )
    async with response_ctx as response:
        assert response.status == 200
        assert not deadline.expired
