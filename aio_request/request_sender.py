from abc import ABC, abstractmethod

from .base import ClosableResponse, Request
from .deadline import Deadline
from .priority import Priority


class RequestSender(ABC):
    __slots__ = ()

    @abstractmethod
    async def send(self, request: Request, deadline: Deadline, priority: Priority) -> ClosableResponse:
        ...
