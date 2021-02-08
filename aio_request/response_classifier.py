import abc
import enum

from .base import Response


class ResponseVerdict(enum.Enum):
    ACCEPT = 1
    REJECT = 2


class ResponseClassifier(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def classify(self, response: Response) -> ResponseVerdict:
        ...


class DefaultResponseClassifier(ResponseClassifier):
    __slots__ = ("_network_errors_code",)

    def __init__(self, network_errors_code: int = 489):
        self._network_errors_code = network_errors_code

    def classify(self, response: Response) -> ResponseVerdict:
        if response.is_server_error():
            return ResponseVerdict.REJECT
        if response.status == self._network_errors_code:
            return ResponseVerdict.REJECT
        if response.status == 408:
            return ResponseVerdict.REJECT
        return ResponseVerdict.ACCEPT
