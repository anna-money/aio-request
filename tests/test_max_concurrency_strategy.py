import asyncio

import aio_request


async def test_within_limit(client) -> None:
    origin_strategy = aio_request.single_attempt_strategy()
    limiter_strategy = aio_request.max_concurrency_strategy(strategy=origin_strategy, limit=10)

    async def run():
        response_ctx = client().request(
            aio_request.get("?delay=1"),
            deadline=aio_request.Deadline.from_timeout(2),
            strategy=limiter_strategy,
        )
        async with response_ctx as response:
            assert response.status == 200

    await asyncio.gather(
        asyncio.create_task(run()),
        asyncio.create_task(run()),
        asyncio.create_task(run()),
        asyncio.create_task(run()),
        asyncio.create_task(run()),
    )


async def test_beyond_limit(client) -> None:
    origin_strategy = aio_request.single_attempt_strategy()
    limiter_strategy = aio_request.max_concurrency_strategy(strategy=origin_strategy, limit=3)

    async def run():
        response_ctx = client().request(
            aio_request.get("?delay=1"),
            deadline=aio_request.Deadline.from_timeout(3),
            strategy=limiter_strategy,
        )
        async with response_ctx as response:
            assert response.status == 200

    await asyncio.gather(
        asyncio.create_task(run()),
        asyncio.create_task(run()),
        asyncio.create_task(run()),
        asyncio.create_task(run()),
        asyncio.create_task(run()),
    )
