import multidict
import yarl
from aiohttp import ClientSession

import aio_request


async def test_success_with_path_parameters():
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


async def test_success_with_query_parameters():
    async with ClientSession() as client_session:
        transport = aio_request.AioHttpTransport(client_session)
        response = await transport.send(
            yarl.URL("https://httpbin.org/"),
            aio_request.get("anything", query_parameters={"a": "b"}),
            5,
        )
        try:
            assert response.status == 200
            response_json = await response.json()
            assert response_json["args"] == {"a": "b"}
        finally:
            await response.close()


async def test_success_with_query_parameters_multidict():
    async with ClientSession() as client_session:
        transport = aio_request.AioHttpTransport(client_session)
        query_parameters = multidict.CIMultiDict[str]()
        query_parameters.add("a", "b")
        query_parameters.add("a", "c")
        response = await transport.send(
            yarl.URL("https://httpbin.org/"),
            aio_request.get("anything", query_parameters=query_parameters),
            5,
        )
        try:
            assert response.status == 200
            response_json = await response.json()
            assert response_json["args"] == {"a": ["b", "c"]}
        finally:
            await response.close()
