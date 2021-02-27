import abc

import yarl

from .base import ClosableResponse, Request


class Transport(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def send(self, endpoint: yarl.URL, request: Request, timeout: float) -> ClosableResponse:
        ...
