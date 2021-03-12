import aio_request


async def test_success(client: aio_request.Client) -> None:
    response_ctx = client().request(
        aio_request.get("?delay=1"),
        deadline=aio_request.Deadline.from_timeout(1.5),
        strategy=aio_request.sequential_strategy(),
    )
    async with response_ctx as response:
        assert response.status == 200


async def test_not_enough_timeout(client: aio_request.Client) -> None:
    response_ctx = client().request(
        aio_request.get("?delay=1"),
        deadline=aio_request.Deadline.from_timeout(0.5),
        strategy=aio_request.sequential_strategy(),
    )
    async with response_ctx as response:
        assert response.status == 408


async def test_expired_budget(client: aio_request.Client) -> None:
    response_ctx = client().request(
        aio_request.get("?delay=1"),
        deadline=aio_request.Deadline.from_timeout(0),
        strategy=aio_request.sequential_strategy(),
    )
    async with response_ctx as response:
        assert response.status == 408


async def test_low_timeout_threshold(client):
    response_ctx = client().request(
        aio_request.get("?delay=1"),
        deadline=aio_request.Deadline.from_timeout(0.005),
        strategy=aio_request.sequential_strategy(),
    )
    async with response_ctx as response:
        assert response.status == 408


async def test_func_handler_timeout(client):
    deadline = aio_request.Deadline.from_timeout(1)
    response_ctx = client(emit_system_headers=False).request(
        aio_request.get("with_timeout?delay=1"),
        deadline=deadline,
        strategy=aio_request.sequential_strategy(),
    )
    async with response_ctx as response:
        assert response.status == 408
        assert not deadline.expired


async def test_view_handler_timeout(client):
    deadline = aio_request.Deadline.from_timeout(1)
    response_ctx = client(emit_system_headers=False).request(
        aio_request.get("view_with_timeout?delay=1"),
        deadline=deadline,
        strategy=aio_request.sequential_strategy(),
    )
    async with response_ctx as response:
        assert response.status == 408
        assert not deadline.expired
