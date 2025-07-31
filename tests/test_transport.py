import unittest.mock

import aiohttp
import httpx
import multidict
import pytest
import yarl

import aio_request

DEFAULT_TIMEOUT = 20.0


@pytest.fixture(params=("aiohttp", "httpx"))
async def transport(request):
    if request.param == "aiohttp":
        async with aiohttp.ClientSession() as client_session:
            yield aio_request.AioHttpTransport(client_session)
    elif request.param == "httpx":
        async with httpx.AsyncClient() as async_client:
            yield aio_request.HttpxTransport(async_client)
    else:
        raise ValueError(f"Unknown transport {request.param}")


async def test_success_with_path_parameters(httpbin, transport):
    response = await transport.send(
        yarl.URL(httpbin.url),
        aio_request.get("status/{status}", path_parameters={"status": "200"}),
        DEFAULT_TIMEOUT,
    )
    try:
        assert response.status == 200
    finally:
        await response.close()


async def test_json(httpbin, transport):
    response = await transport.send(
        yarl.URL(httpbin.url),
        aio_request.get("json"),
        DEFAULT_TIMEOUT,
    )
    try:
        assert response.status == 200
        assert await response.json() == {
            "slideshow": {
                "author": "Yours Truly",
                "date": "date of publication",
                "slides": [
                    {"title": "Wake up to WonderWidgets!", "type": "all"},
                    {
                        "items": ["Why <em>WonderWidgets</em> are great", "Who <em>buys</em> WonderWidgets"],
                        "title": "Overview",
                        "type": "all",
                    },
                ],
                "title": "Sample Slide Show",
            }
        }
        assert response.headers == multidict.CIMultiDict[str](
            {
                "Date": unittest.mock.ANY,
                "Server": "Pytest-HTTPBIN/0.1.0",
                "Content-Type": "application/json",
                "Content-Length": "275",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "true",
                "Connection": "Close",
            }
        )
    finally:
        await response.close()


async def test_json_empty_response(httpbin, transport):
    response = await transport.send(
        yarl.URL(httpbin.url),
        aio_request.post("status/200"),
        DEFAULT_TIMEOUT,
    )
    try:
        assert response.status == 200
        assert await response.json(content_type=None) == None
        assert response.headers == multidict.CIMultiDict[str](
            {
                "Date": unittest.mock.ANY,
                "Server": "Pytest-HTTPBIN/0.1.0",
                "Content-Type": "text/html; charset=utf-8",
                "Content-Length": "0",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "true",
                "Connection": "Close",
            }
        )
    finally:
        await response.close()


async def test_utf8_text(httpbin, transport):
    response = await transport.send(
        yarl.URL(httpbin.url),
        aio_request.get("encoding/utf8"),
        DEFAULT_TIMEOUT,
    )
    try:
        assert response.status == 200
        assert len(await response.text()) == 7808
    finally:
        await response.close()


async def test_success_with_query_parameters(httpbin, transport):
    response = await transport.send(
        yarl.URL(httpbin.url),
        aio_request.get("anything", query_parameters={"a": "b"}),
        DEFAULT_TIMEOUT,
    )
    try:
        assert response.status == 200
        response_json = await response.json()
        assert response_json["args"] == {"a": "b"}
    finally:
        await response.close()


async def test_success_with_query_parameters_multidict(httpbin, transport):
    query_parameters = multidict.CIMultiDict[str]()
    query_parameters.add("a", "b")
    query_parameters.add("a", "c")
    response = await transport.send(
        yarl.URL(httpbin.url),
        aio_request.get("anything", query_parameters=query_parameters),
        DEFAULT_TIMEOUT,
    )
    try:
        assert response.status == 200
        response_json = await response.json()
        assert response_json["args"] == {"a": ["b", "c"]}
    finally:
        await response.close()


async def test_redirects_max_redirects(httpbin, transport):
    response = await transport.send(
        yarl.URL(f"{httpbin.url}/absolute-redirect/10"),
        aio_request.get("", allow_redirects=True, max_redirects=2),
        DEFAULT_TIMEOUT,
    )
    assert response.status == 488
    assert response.headers.getall(aio_request.Header.LOCATION) == [
        f"{httpbin.url}/absolute-redirect/9",
        f"{httpbin.url}/absolute-redirect/8",
    ]
    assert not await response.read()


async def test_redirects_not_allowed(httpbin, transport):
    response = await transport.send(
        yarl.URL(f"{httpbin.url}/absolute-redirect/10"),
        aio_request.get("", allow_redirects=False),
        DEFAULT_TIMEOUT,
    )
    assert response.status == 302
    assert response.headers["Location"] == f"{httpbin.url}/absolute-redirect/9"


async def test_redirects_allowed_default(httpbin, transport):
    response = await transport.send(
        yarl.URL(f"{httpbin.url}/absolute-redirect/5"),
        aio_request.get(""),
        DEFAULT_TIMEOUT,
    )
    assert response.status == 200
