import yarl
from aiohttp import ClientSession

import aio_request


async def test_success(request_strategies_factory):
    async with ClientSession() as client_session:
        transport = aio_request.AioHttpTransport(client_session)
        response = await transport.send(
            yarl.URL("https://httpbin.org/"),
            aio_request.get("status/{status}", path_parameters={"status": "200"}),
            5,
        )
        try:
            assert response.status == 200
        finally:
            await response.close()
