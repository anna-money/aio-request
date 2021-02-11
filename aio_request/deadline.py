import datetime
import time
from typing import Optional

INITIAL_TIMESTAMP = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).timestamp()


class Deadline:
    @staticmethod
    def from_timeout(timeout: float) -> "Deadline":
        return Deadline(time.time() + timeout)

    @staticmethod
    def try_parse(value: Optional[str]) -> Optional["Deadline"]:
        if value is None:
            return None
        try:
            return Deadline(float(value))
        except ValueError:
            return None

    __slots__ = ("_deadline_at",)

    def __init__(self, deadline_at: float):
        if deadline_at < INITIAL_TIMESTAMP:
            raise RuntimeError(f"Invalid deadline_at {deadline_at}: should be >= {INITIAL_TIMESTAMP}")

        self._deadline_at = deadline_at

    @property
    def timeout(self) -> float:
        return max(self._deadline_at - time.time(), 0.001)  # 0 is infinite

    @property
    def expired(self) -> bool:
        return self._deadline_at - time.time() <= 0

    def __str__(self) -> str:
        return str(self._deadline_at)
