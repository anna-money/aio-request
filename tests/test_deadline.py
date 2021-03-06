import asyncio
import datetime

import aio_request

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

import pytest


async def test_deadline_expired():
    deadline = aio_request.Deadline.from_timeout(1)
    assert not deadline.expired
    assert 0.5 < deadline.timeout < 1
    await asyncio.sleep(1)
    assert deadline.expired


async def test_invalid_deadline_at():
    with pytest.raises(RuntimeError):
        aio_request.Deadline(datetime.datetime.utcnow().replace(tzinfo=zoneinfo.ZoneInfo("UTC")))


async def test_parse_str():
    deadline = aio_request.Deadline.from_timeout(1)
    assert deadline.deadline_at == aio_request.Deadline.try_parse(str(deadline)).deadline_at
