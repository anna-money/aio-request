import abc
import asyncio
import collections.abc

import yarl


class EndpointProvider(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def get(self) -> yarl.URL: ...


class StaticEndpointProvider(EndpointProvider):
    __slots__ = ("__endpoint",)

    def __init__(self, endpoint: str | yarl.URL) -> None:
        self.__endpoint = ensure_url(endpoint)

    async def get(self) -> yarl.URL:
        return self.__endpoint


EndpointDelegate = collections.abc.Callable[[], str | yarl.URL]
AsyncEndpointDelete = collections.abc.Callable[[], collections.abc.Awaitable[str | yarl.URL]]


class DelegateEndpointProvider(EndpointProvider):
    __slots__ = ("__endpoint_delegate",)

    def __init__(self, endpoint_delegate: EndpointDelegate | AsyncEndpointDelete) -> None:
        self.__endpoint_delegate = endpoint_delegate

    async def get(self) -> yarl.URL:
        endpoint = self.__endpoint_delegate()
        if asyncio.iscoroutine(endpoint):
            endpoint = await endpoint
        return ensure_url(endpoint)  # type: ignore


def ensure_url(endpoint: str | yarl.URL) -> yarl.URL:
    if isinstance(endpoint, yarl.URL):
        return endpoint
    return yarl.URL(endpoint)
