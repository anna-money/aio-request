from abc import ABC, abstractmethod
from enum import Enum

from .base import Response


class ResponseVerdict(Enum):
    ACCEPT = 1
    REJECT = 2


class ResponseClassifier(ABC):
    __slots__ = ()

    @abstractmethod
    def classify(self, response: Response) -> ResponseVerdict:
        ...


class DefaultResponseClassifier(ResponseClassifier):
    __slots__ = ("_network_errors_code",)

    def __init__(self, network_errors_code: int = 499):
        self._network_errors_code = network_errors_code

    def classify(self, response: Response) -> ResponseVerdict:
        if response.is_server_error():
            return ResponseVerdict.REJECT
        if response.status == self._network_errors_code:
            return ResponseVerdict.REJECT
        if response.status == 408:
            return ResponseVerdict.REJECT
        return ResponseVerdict.ACCEPT
