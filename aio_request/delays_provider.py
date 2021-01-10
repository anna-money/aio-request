from random import random
from typing import Callable

DELAY_PROVIDER = Callable[[int], float]


def constant_delays(*, delay: float = 0, jitter: float = 0.2) -> DELAY_PROVIDER:
    def _constant(_: int) -> float:
        jitter_amount = delay * random() * jitter
        if random() < 0.5:
            jitter_amount = -jitter_amount
        return delay + jitter_amount

    return _constant


def linear_delays(
    *, min_delay_seconds: float = 0, delay_multiplier: float = 0.05, jitter: float = 0.2
) -> DELAY_PROVIDER:
    def _linear(attempt: int) -> float:
        delay = min_delay_seconds + attempt * delay_multiplier
        jitter_amount = delay * random() * jitter
        if random() < 0.5:
            jitter_amount = -jitter_amount
        return delay + jitter_amount

    return _linear
