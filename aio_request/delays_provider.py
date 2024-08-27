import collections.abc
import random

DELAYS_PROVIDER = collections.abc.Callable[[int], float]


def constant_delays(*, delay: float = 0) -> DELAYS_PROVIDER:
    return lambda _: delay


def linear_backoff_delays(
    *, min_delay_seconds: float = 0, delay_multiplier: float = 0.05, jitter: float = 0.2
) -> DELAYS_PROVIDER:
    def _linear(attempt: int) -> float:
        delay = min_delay_seconds + attempt * delay_multiplier
        jitter_amount = delay * random.random() * jitter
        if random.random() < 0.5:
            jitter_amount = -jitter_amount
        return delay + jitter_amount

    return _linear


linear_delays = linear_backoff_delays
