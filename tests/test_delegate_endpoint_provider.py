import asyncio

import yarl

import aio_request


async def test_delegate_endpoint() -> None:
    provider = aio_request.DelegateEndpointProvider(lambda: "http://example.com")
    assert await provider.get() == yarl.URL("http://example.com")


async def test_delegate_endpoint_async() -> None:
    async def get_endpoint() -> str | yarl.URL:
        await asyncio.sleep(0)
        return "http://example.com"

    provider = aio_request.DelegateEndpointProvider(get_endpoint)
    assert await provider.get() == yarl.URL("http://example.com")
