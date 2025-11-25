import abc

from .base import Request


class RequestAttemptDelaysProvider(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def __call__(self, request: Request, attempt: int) -> float: ...
