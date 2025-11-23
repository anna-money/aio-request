import aio_request

from .conftest import FakeTransport


async def test_setup_with_defaults() -> None:
    client = aio_request.setup(
        transport=FakeTransport(200),
        endpoint="http://test.com",
    )
    async with client.request(aio_request.get("/")) as response:
        assert response.status == 200


async def test_setup_v2_with_defaults() -> None:
    client = aio_request.setup_v2(
        transport=FakeTransport(200),
        endpoint="http://test.com",
    )
    async with client.request(aio_request.get("/")) as response:
        assert response.status == 200
