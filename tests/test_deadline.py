import asyncio
import datetime
import zoneinfo

import aio_request


async def test_deadline_expired():
    deadline = aio_request.Deadline.from_timeout(1)
    assert not deadline.expired
    assert 0.5 < deadline.timeout < 1
    await asyncio.sleep(1)
    assert deadline.expired


async def test_no_timezone_deadline_at():
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    deadline = aio_request.Deadline(now + datetime.timedelta(seconds=1))
    assert not deadline.expired
    assert 0.5 < deadline.timeout < 1.0


async def test_utc_timezone_deadline_at_1():
    now = datetime.datetime.now(datetime.timezone.utc)
    deadline = aio_request.Deadline(now + datetime.timedelta(seconds=1))
    assert not deadline.expired
    assert 0.5 < deadline.timeout < 1.0


async def test_utc_timezone_deadline_at_2():
    utc_timezone = zoneinfo.ZoneInfo("UTC")
    now = datetime.datetime.now(utc_timezone)
    deadline = aio_request.Deadline(now + datetime.timedelta(seconds=1))
    assert not deadline.expired
    assert 0.5 < deadline.timeout < 1.0


async def test_los_angeles_timezone_deadline():
    los_angeles_timezone = zoneinfo.ZoneInfo("America/Los_Angeles")
    now = datetime.datetime.now(los_angeles_timezone)
    deadline = aio_request.Deadline(now + datetime.timedelta(seconds=1))
    assert not deadline.expired
    assert 0.5 < deadline.timeout < 1.0


async def test_parse_str():
    deadline = aio_request.Deadline.from_timeout(1)
    parsed_deadline = aio_request.Deadline.try_parse(str(deadline))
    assert parsed_deadline is not None
    assert deadline.deadline_at == parsed_deadline.deadline_at
