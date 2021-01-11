import time


class Deadline:
    @staticmethod
    def after_seconds(seconds: float) -> "Deadline":
        return Deadline(time.time() + seconds)

    __slots__ = ("_deadline_at",)

    def __init__(self, deadline_at: float):
        self._deadline_at = deadline_at

    @property
    def timeout(self) -> float:
        return max(self._deadline_at - time.time(), 0.001)  # 0 is infinite

    @property
    def expired(self) -> bool:
        return self._deadline_at - time.time() <= 0

    def __str__(self) -> str:
        return str(self._deadline_at)
