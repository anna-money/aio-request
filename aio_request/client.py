import collections.abc
import contextlib

import yarl

from .base import ClosableResponse, Request, Response
from .context import get_context
from .deadline import Deadline
from .endpoint_provider import EndpointProvider
from .priority import Priority
from .request_strategy import RequestStrategy, ResponseWithVerdict
from .response_classifier import ResponseClassifier


class Client:
    __slots__ = (
        "__endpoint_provider",
        "__response_classifier",
        "__request_strategy",
        "__priority",
        "__timeout",
        "__send_request",
    )

    def __init__(
        self,
        *,
        endpoint_provider: EndpointProvider,
        response_classifier: ResponseClassifier,
        request_strategy: RequestStrategy,
        timeout: float,
        priority: Priority,
        send_request: collections.abc.Callable[
            [yarl.URL, Request, Deadline, Priority], collections.abc.Awaitable[ClosableResponse]
        ],
    ):
        self.__endpoint_provider = endpoint_provider
        self.__response_classifier = response_classifier
        self.__request_strategy = request_strategy
        self.__priority = priority
        self.__timeout = timeout
        self.__send_request = send_request

    @contextlib.asynccontextmanager
    async def request(
        self,
        request: Request,
        *,
        deadline: Deadline | None = None,
        priority: Priority | None = None,
        strategy: RequestStrategy | None = None,
    ) -> collections.abc.AsyncIterator[Response]:
        context = get_context()
        response_ctx = (strategy or self.__request_strategy).request(
            self.__send,
            await self.__endpoint_provider.get(),
            request,
            deadline or context.deadline or Deadline.from_timeout(self.__timeout),
            self.__normalize_priority(priority or self.__priority, context.priority),
        )
        async with response_ctx as response_with_verdict:
            yield response_with_verdict.response

    async def __send(
        self,
        endpoint: yarl.URL,
        request: Request,
        deadline: Deadline,
        priority: Priority,
    ) -> ResponseWithVerdict[ClosableResponse]:
        response = await self.__send_request(endpoint, request, deadline, priority)
        return ResponseWithVerdict(response, self.__response_classifier.classify(response))

    @staticmethod
    def __normalize_priority(priority: Priority, context_priority: Priority | None) -> Priority:
        if context_priority is None:
            return priority

        if priority == Priority.LOW and context_priority == Priority.HIGH:
            return Priority.NORMAL

        if priority == Priority.HIGH and context_priority == Priority.LOW:
            return Priority.NORMAL

        return priority
