import aio_request
from tests.conftest import FakeRequestSender


async def test_setup_with_defaults():
    client = aio_request.setup(transport=FakeRequestSender([200]), endpoint="http://test.com")
    async with client.request(aio_request.get("/")) as response:
        assert response.status == 200
