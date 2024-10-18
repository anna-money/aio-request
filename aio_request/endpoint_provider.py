import abc
import asyncio
from typing import Awaitable, Callable

import yarl


class EndpointProvider(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def get(self) -> yarl.URL: ...


class StaticEndpointProvider(EndpointProvider):
    __slots__ = ("__endpoint",)

    def __init__(self, endpoint: str | yarl.URL):
        self.__endpoint = ensure_url(endpoint)

    async def get(self) -> yarl.URL:
        return self.__endpoint


class DelegateEndpointProvider(EndpointProvider):
    __slots__ = ("__provider",)

    def __init__(self, provider: Callable[[], str | yarl.URL] | Callable[[], Awaitable[str | yarl.URL]]):
        self.__provider = provider

    async def get(self) -> yarl.URL:
        result = self.__provider()
        return ensure_url(await result if asyncio.iscoroutine(result) else result)  # type: ignore


def ensure_url(endpoint: str | yarl.URL) -> yarl.URL:
    if isinstance(endpoint, yarl.URL):
        return endpoint
    return yarl.URL(endpoint)
