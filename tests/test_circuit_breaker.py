import asyncio
from typing import Awaitable, Callable

import aio_request


def do(result: int) -> Callable[[], Awaitable[int]]:
    async def _do() -> int:
        return result

    return _do


def is_200(result: int) -> bool:
    return result == 200


async def test_circuit_breaker_should_be_closed_because_of_expire_metrics() -> None:
    circuit_breaker = aio_request.DefaultCircuitBreaker[str, int](
        break_duration=1.0,
        sampling_duration=1.0,
        minimum_throughput=2,
        failure_threshold=0.5,
    )
    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.CLOSED}

    await asyncio.sleep(1)

    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.CLOSED}


async def test_circuit_breaker_should_be_opened_because_of_expire_metrics() -> None:
    circuit_breaker = aio_request.DefaultCircuitBreaker[str, int](
        break_duration=1.0,
        sampling_duration=1.0,
        minimum_throughput=2,
        failure_threshold=0.5,
    )
    assert await circuit_breaker.execute(scope="scope", operation=do(200), fallback=503, is_successful=is_200) == 200
    assert await circuit_breaker.execute(scope="scope", operation=do(200), fallback=503, is_successful=is_200) == 200
    assert await circuit_breaker.execute(scope="scope", operation=do(200), fallback=503, is_successful=is_200) == 200
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.CLOSED}

    await asyncio.sleep(1)

    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.OPENED}


async def test_circuit_breaker_should_close_after_success() -> None:
    circuit_breaker = aio_request.DefaultCircuitBreaker[str, int](
        break_duration=1.0,
        sampling_duration=1.0,
        minimum_throughput=2,
        failure_threshold=0.5,
    )

    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 503

    await asyncio.sleep(1)

    assert await circuit_breaker.execute(scope="scope", operation=do(200), fallback=503, is_successful=is_200) == 200
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.CLOSED}


async def test_circuit_breaker_should_close_after_failure() -> None:
    circuit_breaker = aio_request.DefaultCircuitBreaker[str, int](
        break_duration=1.0,
        sampling_duration=5.0,
        minimum_throughput=2,
        failure_threshold=0.5,
    )

    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 503
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.OPENED}

    await asyncio.sleep(1)

    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.OPENED}
