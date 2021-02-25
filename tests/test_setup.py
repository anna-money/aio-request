import aio_request
from tests.conftest import FakeRequestSender


async def test_setup_with_defaults():
    client = aio_request.setup(request_sender=FakeRequestSender([200]), base_url="http://test.com")
    async with client.request(aio_request.get("/")) as response:
        assert response.status == 200
