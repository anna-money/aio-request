import asyncio

import yarl

import aio_request


async def test_circuit_breaker() -> None:
    circuit_breaker = aio_request.DefaultCircuitBreaker(
        block_duration=1.0, sampling_duration=5.0, minimum_throughput=1, failure_threshold=0.5, windows_count=10
    )
    endpoint = yarl.URL("https://www.google.ru")

    assert circuit_breaker.on_execute(endpoint)
    circuit_breaker.on_failure(endpoint)

    assert not circuit_breaker.on_execute(endpoint)

    await asyncio.sleep(5)  # block_duration

    assert circuit_breaker.on_execute(endpoint)
