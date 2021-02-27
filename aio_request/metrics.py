import abc
from typing import Optional

from .base import Request, Response


class ClientMetricsCollector(abc.ABC):
    __slots__ = ("_service_name",)

    def __init__(self, service_name: str):
        self._service_name = service_name

    @abc.abstractmethod
    def collect(self, request: Request, response: Optional[Response], elapsed_seconds: float) -> None:
        pass


class NoMetricsCollector(ClientMetricsCollector):
    __slots__ = ()

    def collect(self, request: Request, response: Optional[Response], elapsed_seconds: float) -> None:
        pass
