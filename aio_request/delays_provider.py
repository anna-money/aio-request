import collections.abc
import random

DelaysProvider = collections.abc.Callable[[int], float]


def constant_delays(*, delay: float = 0) -> DelaysProvider:
    return lambda _: delay


def linear_backoff_delays(
    *, min_delay_seconds: float = 0, delay_multiplier: float = 0.05, jitter: float = 0.2
) -> DelaysProvider:
    def __linear_backoff_delays(attempt: int) -> float:
        delay = min_delay_seconds + attempt * delay_multiplier
        jitter_amount = delay * random.random() * jitter
        if random.random() < 0.5:
            jitter_amount = -jitter_amount
        return delay + jitter_amount

    return __linear_backoff_delays


linear_delays = linear_backoff_delays
