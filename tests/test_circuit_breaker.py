import asyncio
from typing import Awaitable, Callable

import aio_request


async def test_circuit_breaker() -> None:
    def do(result: int) -> Callable[[], Awaitable[int]]:
        async def _do() -> int:
            return result

        return _do

    circuit_breaker = aio_request.DefaultCircuitBreaker[str, int](
        block_duration=1.0, sampling_duration=5.0, minimum_throughput=1, failure_threshold=0.5, windows_count=10
    )
    assert (
        await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=lambda x: x == 200)
        == 500
    )

    assert (
        await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=lambda x: x == 200)
        == 503
    )

    await asyncio.sleep(5)  # block_duration

    assert (
        await circuit_breaker.execute(scope="scope", operation=do(500), fallback=503, is_successful=lambda x: x == 200)
        == 500
    )
