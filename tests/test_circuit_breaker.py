import asyncio
import collections.abc

import aio_request


def do(result: int) -> collections.abc.Callable[[], collections.abc.Awaitable[int]]:
    async def _do() -> int:
        return result

    return _do


def delay(result: int, *, seconds: float) -> collections.abc.Callable[[], collections.abc.Awaitable[int]]:
    async def _do() -> int:
        await asyncio.sleep(seconds)
        return result

    return _do


def is_200(result: int) -> bool:
    return result == 200


async def test_half_open_to_close() -> None:
    circuit_breaker = aio_request.DefaultCircuitBreaker[str, int](
        break_duration=0.3,
        sampling_duration=1.0,
        minimum_throughput=2,
        failure_threshold=0.5,
        windows_count=1,
    )
    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    await asyncio.sleep(0.3)  # wait break_duration
    delayed_task = asyncio.create_task(
        circuit_breaker.execute(scope="scope", operation=delay(200, seconds=1), fallback=503, is_successful=is_200)
    )
    await asyncio.sleep(0.1)
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.HALF_OPEN}

    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 503
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.HALF_OPEN}

    assert await delayed_task == 200
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.CLOSED}


async def test_half_open_to_open() -> None:
    circuit_breaker = aio_request.DefaultCircuitBreaker[str, int](
        break_duration=0.3,
        sampling_duration=1.0,
        minimum_throughput=2,
        failure_threshold=0.5,
        windows_count=1,
    )
    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    await asyncio.sleep(0.3)  # wait break_duration
    delayed_task = asyncio.create_task(
        circuit_breaker.execute(scope="scope", operation=delay(500, seconds=1), fallback=503, is_successful=is_200)
    )
    await asyncio.sleep(0.1)
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.HALF_OPEN}

    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 503
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.HALF_OPEN}

    assert await delayed_task == 500
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.OPEN}


async def test_circuit_breaker_should_be_closed_because_of_metrics_expire() -> None:
    circuit_breaker = aio_request.DefaultCircuitBreaker[str, int](
        break_duration=1.0,
        sampling_duration=1.0,
        minimum_throughput=2,
        failure_threshold=0.5,
    )
    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.CLOSED}

    await asyncio.sleep(1)  # wait sampling_duration for expiration of metrics

    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.CLOSED}


async def test_circuit_breaker_should_be_opened_because_of_metrics_expire() -> None:
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

    await asyncio.sleep(1)  # wait sampling_duration for expiration of metrics

    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.OPEN}


async def test_circuit_breaker_should_be_closed_after_success() -> None:
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


async def test_circuit_breaker_should_be_open_after_failure() -> None:
    circuit_breaker = aio_request.DefaultCircuitBreaker[str, int](
        break_duration=1.0,
        sampling_duration=5.0,
        minimum_throughput=2,
        failure_threshold=0.5,
    )

    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 503
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.OPEN}

    await asyncio.sleep(1)

    assert await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=is_200) == 500
    assert circuit_breaker.state == {"scope": aio_request.CircuitState.OPEN}
