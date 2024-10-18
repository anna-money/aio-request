import asyncio
from typing import Union

import yarl

import aio_request


async def test_delegate_endpoint():
    provider = aio_request.DelegateEndpointProvider(lambda: "http://example.com")
    assert await provider.get() == yarl.URL("http://example.com")


async def test_delegate_endpoint_async():
    async def get_endpoint() -> Union[str, yarl.URL]:
        await asyncio.sleep(0)
        return "http://example.com"

    provider = aio_request.DelegateEndpointProvider(get_endpoint)
    assert await provider.get() == yarl.URL("http://example.com")
