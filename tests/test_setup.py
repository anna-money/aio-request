import aio_request
from tests.conftest import FakeTransport


async def test_setup_with_defaults():
    client = aio_request.setup(
        transport=FakeTransport([200]),
        endpoint="http://test.com",
    )
    async with client.request(aio_request.get("/")) as response:
        assert response.status == 200
