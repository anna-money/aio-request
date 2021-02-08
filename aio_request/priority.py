import enum
from typing import Optional


class Priority(str, enum.Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

    def __str__(self) -> str:
        return self.value

    @staticmethod
    def parse(value: Optional[str]) -> "Priority":
        if value is None:
            return Priority.NORMAL
        try:
            return Priority(value.lower())
        except ValueError:
            return Priority.NORMAL
