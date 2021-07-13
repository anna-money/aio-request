import abc
import contextlib
from typing import AsyncContextManager, AsyncIterator, Awaitable, Callable, Optional

import yarl

from .base import ClosableResponse, Request, Response
from .context import get_context
from .deadline import Deadline
from .priority import Priority
from .request_strategy import RequestStrategy, ResponseWithVerdict
from .response_classifier import ResponseClassifier


class Client(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def request(
        self,
        request: Request,
        *,
        deadline: Optional[Deadline] = None,
        priority: Optional[Priority] = None,
        strategy: Optional[RequestStrategy] = None,
    ) -> AsyncContextManager[Response]:
        ...


class DefaultClient(Client):
    __slots__ = (
        "_endpoint",
        "_response_classifier",
        "_request_strategy",
        "_priority",
        "_timeout",
        "_send_request",
    )

    def __init__(
        self,
        *,
        endpoint: yarl.URL,
        response_classifier: ResponseClassifier,
        request_strategy: RequestStrategy,
        timeout: float,
        priority: Priority,
        send_request: Callable[[yarl.URL, Request, Deadline, Priority], Awaitable[ClosableResponse]],
    ):
        self._endpoint = endpoint
        self._response_classifier = response_classifier
        self._request_strategy = request_strategy
        self._priority = priority
        self._timeout = timeout
        self._send_request = send_request

    def request(
        self,
        request: Request,
        *,
        deadline: Optional[Deadline] = None,
        priority: Optional[Priority] = None,
        strategy: Optional[RequestStrategy] = None,
    ) -> AsyncContextManager[Response]:
        return self._request(request, deadline=deadline, priority=priority, strategy=strategy)

    @contextlib.asynccontextmanager
    async def _request(
        self,
        request: Request,
        *,
        deadline: Optional[Deadline] = None,
        priority: Optional[Priority] = None,
        strategy: Optional[RequestStrategy] = None,
    ) -> AsyncIterator[Response]:
        context = get_context()
        response_ctx = (strategy or self._request_strategy).request(
            self._send,
            self._endpoint,
            request,
            deadline or context.deadline or Deadline.from_timeout(self._timeout),
            self.normalize_priority(priority or self._priority, context.priority),
        )
        async with response_ctx as response:
            yield response.response

    @staticmethod
    def normalize_priority(priority: Priority, context_priority: Optional[Priority]) -> Priority:
        if context_priority is None:
            return priority

        if priority == Priority.LOW and context_priority == Priority.HIGH:
            return Priority.NORMAL

        if priority == Priority.HIGH and context_priority == Priority.LOW:
            return Priority.NORMAL

        return priority

    async def _send(
        self, endpoint: yarl.URL, request: Request, deadline: Deadline, priority: Priority
    ) -> ResponseWithVerdict[ClosableResponse]:
        response = await self._send_request(endpoint, request, deadline, priority)
        return ResponseWithVerdict(response, self._response_classifier.classify(response))
