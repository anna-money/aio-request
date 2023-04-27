import aiohttp
import multidict
import pytest
import yarl

import aio_request

DEFAULT_TIMEOUT = 20.0


@pytest.mark.skip(reason="httpbin issues")
async def test_success_with_path_parameters():
    async with aiohttp.ClientSession() as client_session:
        transport = aio_request.AioHttpTransport(client_session)
        response = await transport.send(
            yarl.URL("https://httpbin.org/"),
            aio_request.get("status/{status}", path_parameters={"status": "200"}),
            DEFAULT_TIMEOUT,
        )
        try:
            assert response.status == 200
        finally:
            await response.close()


@pytest.mark.skip(reason="httpbin issues")
async def test_success_with_query_parameters():
    async with aiohttp.ClientSession() as client_session:
        transport = aio_request.AioHttpTransport(client_session)
        response = await transport.send(
            yarl.URL("https://httpbin.org/"),
            aio_request.get("anything", query_parameters={"a": "b"}),
            DEFAULT_TIMEOUT,
        )
        try:
            assert response.status == 200
            response_json = await response.json()
            assert response_json["args"] == {"a": "b"}
        finally:
            await response.close()


@pytest.mark.skip(reason="httpbin issues")
async def test_success_with_query_parameters_multidict():
    async with aiohttp.ClientSession() as client_session:
        transport = aio_request.AioHttpTransport(client_session)
        query_parameters = multidict.CIMultiDict[str]()
        query_parameters.add("a", "b")
        query_parameters.add("a", "c")
        response = await transport.send(
            yarl.URL("https://httpbin.org/"),
            aio_request.get("anything", query_parameters=query_parameters),
            DEFAULT_TIMEOUT,
        )
        try:
            assert response.status == 200
            response_json = await response.json()
            assert response_json["args"] == {"a": ["b", "c"]}
        finally:
            await response.close()


@pytest.mark.skip(reason="httpbin issues")
async def test_redirects_max_redirects():
    async with aiohttp.ClientSession() as client_session:
        transport = aio_request.AioHttpTransport(client_session)

        response = await transport.send(
            yarl.URL("http://httpbin.org/absolute-redirect/10"),
            aio_request.get("", allow_redirects=True, max_redirects=2),
            DEFAULT_TIMEOUT,
        )
        assert response.status == 488
        assert response.headers.getall(aio_request.Header.LOCATION) == [
            "http://httpbin.org/absolute-redirect/9",
            "http://httpbin.org/absolute-redirect/8",
        ]
        assert not await response.read()


@pytest.mark.skip(reason="httpbin issues")
async def test_redirects_not_allowed():
    async with aiohttp.ClientSession() as client_session:
        transport = aio_request.AioHttpTransport(client_session)
        response = await transport.send(
            yarl.URL("http://httpbin.org/absolute-redirect/10"),
            aio_request.get("", allow_redirects=False),
            DEFAULT_TIMEOUT,
        )
        assert response.status == 302
        assert response.headers["Location"] == "http://httpbin.org/absolute-redirect/9"


@pytest.mark.skip(reason="httpbin issues")
async def test_redirects_allowed_default():
    async with aiohttp.ClientSession() as client_session:
        transport = aio_request.AioHttpTransport(client_session)
        response = await transport.send(
            yarl.URL("http://httpbin.org/absolute-redirect/5"),
            aio_request.get(""),
            DEFAULT_TIMEOUT,
        )
        assert response.status == 200
