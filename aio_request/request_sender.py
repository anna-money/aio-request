import abc

import yarl

from .base import ClosableResponse, Request


class RequestSender(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def send(self, endpoint_url: yarl.URL, request: Request, timeout: float) -> ClosableResponse:
        ...
