from abc import ABC, abstractmethod

from .base import Request, ClosableResponse
from .deadline import Deadline


class RequestSender(ABC):
    __slots__ = ()

    @abstractmethod
    async def send(self, request: Request, deadline: Deadline) -> ClosableResponse:
        ...
