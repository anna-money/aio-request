import datetime


class Deadline:
    @staticmethod
    def from_timeout(seconds: float) -> "Deadline":
        return Deadline(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds))

    @staticmethod
    def try_parse(value: str | None) -> "Deadline | None":
        if value is None:
            return None
        try:
            return Deadline(datetime.datetime.fromisoformat(value))
        except ValueError:
            return None

    __slots__ = ("deadline_at",)

    deadline_at: datetime.datetime

    def __init__(self, deadline_at: datetime.datetime):
        if deadline_at.tzinfo is None:
            self.deadline_at = deadline_at.replace(tzinfo=datetime.timezone.utc)
        else:
            self.deadline_at = deadline_at

    @property
    def timeout(self) -> float:
        return max(
            (self.deadline_at - datetime.datetime.now(datetime.timezone.utc)).total_seconds(), 0.001
        )  # 0 is infinite

    @property
    def expired(self) -> bool:
        return (self.deadline_at - datetime.datetime.now(datetime.timezone.utc)).total_seconds() <= 0

    def __repr__(self) -> str:
        return f"<Deadline [{self.deadline_at.isoformat()}]>"

    def __str__(self) -> str:
        return str(self.deadline_at.isoformat())
