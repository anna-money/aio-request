from abc import ABC, abstractmethod
from enum import Enum

from .models import Response


class ResponseVerdict(Enum):
    ACCEPT = 1
    REJECT = 2


class ResponseClassifier(ABC):
    __slots__ = ()

    @abstractmethod
    def classify(self, response: Response) -> ResponseVerdict:
        ...


def is_successful_response(response: Response) -> bool:
    return 200 <= response.code < 300


def is_client_error_response(response: Response) -> bool:
    return 400 <= response.code < 500


def is_server_error_response(response: Response) -> bool:
    return response.code > 500


class DefaultResponseClassifier(ResponseClassifier):
    __slots__ = ("_network_errors_code",)

    def __init__(self, network_errors_code: int = 499):
        self._network_errors_code = network_errors_code

    def classify(self, response: Response) -> ResponseVerdict:
        if is_server_error_response(response):
            return ResponseVerdict.REJECT
        if response.code == self._network_errors_code:
            return ResponseVerdict.REJECT
        if response.code == 408:
            return ResponseVerdict.REJECT
        return ResponseVerdict.ACCEPT
