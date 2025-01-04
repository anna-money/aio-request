import time
from typing import Any


class Deadline:
    @staticmethod
    def from_timeout(seconds: float) -> "Deadline":
        if seconds < 0:
            raise ValueError("seconds cannot be negative")

        return Deadline(started_at=time.perf_counter(), seconds=seconds)

    __slots__ = ("__seconds", "__started_at")

    def __init__(self, started_at: float, seconds: float):
        self.__seconds = seconds
        self.__started_at = started_at

    @property
    def timeout(self) -> float:
        remaining = self.__seconds - self.__get_elapsed()
        return remaining if remaining > 0 else 0

    @property
    def expired(self) -> bool:
        return self.__seconds - self.__get_elapsed() <= 0

    def __truediv__(self, divisor: Any) -> "Deadline":
        if not isinstance(divisor, (int, float)):
            raise ValueError(f"unsupported operand type(s) for /: 'Deadline' and {type(divisor)}")

        if divisor == 0:
            raise ValueError("division by zero")

        if divisor < 0:
            raise ValueError("division by negative number")

        return Deadline.from_timeout(self.timeout / divisor)

    def __float__(self) -> float:
        return self.timeout

    def __repr__(self) -> str:
        if self.expired:
            return "<Deadline [expired]>"
        return f"<Deadline [timeout={self.timeout}]>"

    def __get_elapsed(self) -> float:
        return time.perf_counter() - self.__started_at
