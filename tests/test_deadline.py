import asyncio

import pytest

from aio_request import Deadline


async def test_deadline_expired():
    deadline = Deadline.after_seconds(seconds=1)
    assert not deadline.expired
    assert 0.5 < deadline.timeout < 1
    await asyncio.sleep(1)
    assert deadline.expired


async def test_invalid_deadline_at():
    with pytest.raises(RuntimeError):
        Deadline(5)
