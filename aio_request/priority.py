import enum


class Priority(enum.StrEnum):
    HIGH = enum.auto()
    NORMAL = enum.auto()
    LOW = enum.auto()

    @staticmethod
    def try_parse(value: str | None) -> "Priority | None":
        if value is None:
            return None
        try:
            return Priority(value.lower())
        except ValueError:
            return None
