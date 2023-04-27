import abc
import enum
from typing import Dict, Optional

from .base import Header, Response


class ResponseVerdict(enum.Enum):
    ACCEPT = 1
    REJECT = 2


class ResponseClassifier(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def classify(self, response: Response) -> ResponseVerdict:
        ...


class DefaultResponseClassifier(ResponseClassifier):
    __slots__ = (
        "_network_errors_code",
        "_too_many_redirects_code",
        "_verdict_for_status",
    )

    def __init__(
        self,
        network_errors_code: int = 489,
        too_many_redirects_code: int = 488,
        verdict_for_status: Optional[Dict[int, ResponseVerdict]] = None,
    ):
        self._network_errors_code = network_errors_code
        self._too_many_redirects_code = too_many_redirects_code
        self._verdict_for_status = verdict_for_status or {}

    def classify(self, response: Response) -> ResponseVerdict:
        verdict = self._verdict_for_status.get(response.status)
        if verdict is not None:
            return verdict
        if Header.X_DO_NOT_RETRY in response.headers:
            return ResponseVerdict.ACCEPT
        if response.is_server_error():
            return ResponseVerdict.REJECT
        if response.status == self._network_errors_code:
            return ResponseVerdict.REJECT
        if response.status == self._too_many_redirects_code:
            return ResponseVerdict.ACCEPT
        if response.status == 408:
            return ResponseVerdict.REJECT
        if response.status == 429:
            return ResponseVerdict.REJECT
        return ResponseVerdict.ACCEPT
