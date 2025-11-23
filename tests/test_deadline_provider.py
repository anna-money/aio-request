import asyncio

import aio_request


async def test_split_deadline_between_attempt() -> None:
    provider = aio_request.split_deadline_between_attempts()
    deadline = aio_request.Deadline.from_timeout(1)

    attempt_deadline = provider(deadline, 0, 3)
    assert 0.3 <= attempt_deadline.timeout <= 0.34

    await asyncio.sleep(0.33)

    attempt_deadline = provider(deadline, 1, 3)
    assert 0.3 <= attempt_deadline.timeout <= 0.34
    await asyncio.sleep(0.33)

    attempt_deadline = provider(deadline, 2, 3)
    assert 0.3 <= attempt_deadline.timeout <= 0.34


async def test_split_deadline_between_attempt_with_split_factor() -> None:
    provider = aio_request.split_deadline_between_attempts(attempts_count_to_split=2)
    deadline = aio_request.Deadline.from_timeout(1)

    attempt_deadline = provider(deadline, 0, 3)
    assert 0.45 <= attempt_deadline.timeout <= 0.5

    await asyncio.sleep(0.33)

    attempt_deadline = provider(deadline, 1, 3)
    assert 0.6 <= attempt_deadline.timeout <= 0.67

    await asyncio.sleep(0.33)

    attempt_deadline = provider(deadline, 2, 3)
    assert 0.3 <= attempt_deadline.timeout <= 0.34


async def test_split_deadline_between_attempts_fast_attempt_failure() -> None:
    provider = aio_request.split_deadline_between_attempts()
    deadline = aio_request.Deadline.from_timeout(1)

    attempt_deadline = provider(deadline, 0, 3)
    assert 0.3 <= attempt_deadline.timeout <= 0.34

    await asyncio.sleep(0.1)  # fast attempt failure

    attempt_deadline = provider(deadline, 1, 3)
    assert 0.4 <= attempt_deadline.timeout <= 0.45
    await asyncio.sleep(0.1)  # fast attempt failure

    attempt_deadline = provider(deadline, 2, 3)
    assert 0.75 <= attempt_deadline.timeout <= 0.8


async def test_split_deadline_between_attempts_fast_attempt_failure_with_split_factor() -> None:
    provider = aio_request.split_deadline_between_attempts(attempts_count_to_split=2)
    deadline = aio_request.Deadline.from_timeout(1)

    attempt_deadline = provider(deadline, 0, 3)
    assert 0.45 <= attempt_deadline.timeout <= 0.5

    await asyncio.sleep(0.1)  # fast attempt failure

    attempt_deadline = provider(deadline, 1, 3)
    assert 0.85 <= attempt_deadline.timeout <= 0.9

    await asyncio.sleep(0.1)  # fast attempt failure

    attempt_deadline = provider(deadline, 2, 3)
    assert 0.75 <= attempt_deadline.timeout <= 0.8
