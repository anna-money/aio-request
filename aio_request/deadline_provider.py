from typing import Callable

from .deadline import Deadline

DeadlineProvider = Callable[[Deadline, int, int], Deadline]


def split_deadline_between_attempts() -> DeadlineProvider:
    """
    Split deadline between attempts.

    Total 3 attempts with 9 second deadline w/o any delays in between attempts.
    We might observe the following deadlines:

    1. 3 sec -> 3 sec -> 3 sec. All attempts have spent a full timeout.

    2. 1 sec -> 1 sec -> 8 sec. Two attempts have spent 1 seconds each,
    the last one has received the remaining 8 seconds due to redistribution.
    """

    def __provider(deadline: Deadline, attempt: int, attempts_count: int) -> Deadline:
        if deadline.expired:
            return deadline

        attempts_left = attempts_count - attempt
        if attempts_left == 0:
            raise ValueError("no attempts left")

        return deadline / attempts_left

    return __provider


def pass_deadline_through() -> DeadlineProvider:
    """
    Pass the remaining deadline to each attempt.
    """
    return lambda deadline, _, __: deadline
