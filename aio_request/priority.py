import enum


class Priority(str, enum.Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"<Priority [{self.value}]>"

    @staticmethod
    def try_parse(value: str | None) -> "Priority | None":
        if value is None:
            return None
        try:
            return Priority(value.lower())
        except ValueError:
            return None
