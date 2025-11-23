import asyncio

import aio_request


async def test_deadline_expired() -> None:
    deadline = aio_request.Deadline.from_timeout(1)
    assert not deadline.expired
    assert 0.5 < deadline.timeout < 1
    await asyncio.sleep(1)
    assert deadline.expired


async def test_deadline_division() -> None:
    deadline = aio_request.Deadline.from_timeout(1)
    assert not deadline.expired
    assert 0.75 < deadline.timeout < 1

    half_deadline = deadline / 2

    assert not half_deadline.expired
    assert 0.25 < half_deadline.timeout < 0.5

    await asyncio.sleep(0.5)

    assert half_deadline.expired
    assert not deadline.expired

    await asyncio.sleep(0.5)

    assert half_deadline.expired
    assert deadline.expired
