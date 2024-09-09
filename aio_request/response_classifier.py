import abc
import enum

from .base import Header, Response


class ResponseVerdict(enum.Enum):
    ACCEPT = enum.auto()
    REJECT = enum.auto()


class ResponseClassifier(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def classify(self, response: Response) -> ResponseVerdict: ...


class DefaultResponseClassifier(ResponseClassifier):
    __slots__ = (
        "__network_errors_code",
        "__too_many_redirects_code",
        "__verdict_for_status",
    )

    def __init__(
        self,
        network_errors_code: int = 489,
        too_many_redirects_code: int = 488,
        verdict_for_status: dict[int, ResponseVerdict] | None = None,
    ):
        self.__network_errors_code = network_errors_code
        self.__too_many_redirects_code = too_many_redirects_code
        self.__verdict_for_status = verdict_for_status or {}

    def classify(self, response: Response) -> ResponseVerdict:
        verdict = self.__verdict_for_status.get(response.status)
        if verdict is not None:
            return verdict
        if Header.X_DO_NOT_RETRY in response.headers:
            return ResponseVerdict.ACCEPT
        if response.is_server_error():
            return ResponseVerdict.REJECT
        if response.status == self.__network_errors_code:
            return ResponseVerdict.REJECT
        if response.status == self.__too_many_redirects_code:
            return ResponseVerdict.ACCEPT
        if response.status == 408:
            return ResponseVerdict.REJECT
        if response.status == 429:
            return ResponseVerdict.REJECT
        return ResponseVerdict.ACCEPT
