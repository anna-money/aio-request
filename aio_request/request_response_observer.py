import abc

from .base import Request, Response


class RequestResponseObserver(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def observe(self, request: Request, response: Response) -> None: ...
