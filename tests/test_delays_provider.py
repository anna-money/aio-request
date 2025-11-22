import aio_request


def test_constant() -> None:
    delays_provider = aio_request.constant_delays(delay=42)
    assert delays_provider(0) == 42
    assert delays_provider(1) == 42
    assert delays_provider(2) == 42


def test_linear_backoff() -> None:
    delays_provider = aio_request.linear_backoff_delays(min_delay_seconds=1, delay_multiplier=2, jitter=0)
    assert delays_provider(0) == 1
    assert delays_provider(1) == 3
    assert delays_provider(2) == 5
