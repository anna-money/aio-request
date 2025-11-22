from collections.abc import Callable

from .deadline import Deadline

DeadlineProvider = Callable[[Deadline, int, int], Deadline]


def split_deadline_between_attempts(*, attempts_count_to_split: int | None = None) -> DeadlineProvider:
    """
    Split deadline between attempts.

    Total 3 attempts with 9 second deadline w/o any delays in between attempts.
    We might observe the following deadlines:

    1. 3 sec -> 3 sec -> 3 sec. All attempts have spent a full timeout.

    2. 1 sec -> 1 sec -> 8 sec. Two attempts have spent 1 seconds each,
    the last one has received the remaining 8 seconds due to redistribution.

    If attempts_count_to_split is not None, then the deadline will be split between the first attempts_count_to_split.
    """

    if attempts_count_to_split is not None and attempts_count_to_split < 2:
        raise ValueError("attempts_count_to_split should be greater or equal to 2")

    def __provider(deadline: Deadline, attempt: int, attempts_count: int) -> Deadline:
        if deadline.expired:
            return deadline
        if attempts_count_to_split is None:
            effective_attempts_left = attempts_count - attempt
        else:
            effective_attempts_left = min(attempts_count_to_split, attempts_count) - attempt
        if effective_attempts_left <= 1:
            return deadline
        return deadline / effective_attempts_left

    return __provider


def pass_deadline_through() -> DeadlineProvider:
    """
    Pass the remaining deadline to each attempt.
    """
    return lambda deadline, _, __: deadline
