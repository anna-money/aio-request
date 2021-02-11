import enum
from typing import Optional


class Priority(str, enum.Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

    def __str__(self) -> str:
        return self.value

    @staticmethod
    def try_parse(value: Optional[str]) -> Optional["Priority"]:
        if value is None:
            return None
        try:
            return Priority(value.lower())
        except ValueError:
            return None
