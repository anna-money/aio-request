import abc
from typing import Optional

from .base import Request, Response


class Metrics(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def collect(self, request: Request, response: Optional[Response], elapsed_seconds: float) -> None:
        pass


class NoMetrics(Metrics):
    __slots__ = ()

    def collect(self, request: Request, response: Optional[Response], elapsed_seconds: float) -> None:
        pass
