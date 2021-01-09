from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from .deadline import Deadline
from .models import Request, Response


@dataclass(frozen=True)
class ClosableResponse(Response):
    __slots__ = ("close",)

    close: Callable[[], None]


class RequestSender(ABC):
    __slots__ = ()

    @abstractmethod
    async def send(self, request: Request, deadline: Deadline) -> ClosableResponse:
        ...
