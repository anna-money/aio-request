import abc

from .base import ClosableResponse, Request


class RequestSender(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def send(self, request: Request, timeout: float) -> ClosableResponse:
        ...
