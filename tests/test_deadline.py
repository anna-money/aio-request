import asyncio
import datetime
import zoneinfo

import pytest

import aio_request


async def test_deadline_expired():
    deadline = aio_request.Deadline.from_timeout(1)
    assert not deadline.expired
    assert 0.5 < deadline.timeout < 1
    await asyncio.sleep(1)
    assert deadline.expired


async def test_invalid_deadline_at():
    with pytest.raises(RuntimeError):
        aio_request.Deadline(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=zoneinfo.ZoneInfo("UTC")))


async def test_parse_str():
    deadline = aio_request.Deadline.from_timeout(1)
    parsed_deadline = aio_request.Deadline.try_parse(str(deadline))
    assert parsed_deadline is not None
    assert deadline.deadline_at == parsed_deadline.deadline_at
