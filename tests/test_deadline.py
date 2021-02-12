import asyncio
import datetime
import zoneinfo

import pytest

from aio_request import Deadline


async def test_deadline_expired():
    deadline = Deadline.from_timeout(1)
    assert not deadline.expired
    assert 0.5 < deadline.timeout < 1
    await asyncio.sleep(1)
    assert deadline.expired


async def test_invalid_deadline_at():
    with pytest.raises(RuntimeError):
        Deadline(datetime.datetime.utcnow().replace(tzinfo=zoneinfo.ZoneInfo("UTC")))


async def test_parse_str():
    deadline = Deadline.from_timeout(1)
    assert deadline == Deadline.try_parse(str(deadline))
