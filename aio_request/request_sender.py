import abc

from .base import ClosableResponse, Request
from .deadline import Deadline
from .priority import Priority


class RequestSender(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def send(self, request: Request, deadline: Deadline, priority: Priority) -> ClosableResponse:
        ...
