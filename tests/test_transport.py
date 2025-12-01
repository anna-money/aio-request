import contextlib
import logging
import unittest.mock
from collections.abc import Callable
from typing import Any

import multidict
import pytest
import yarl

import aio_request

DEFAULT_TIMEOUT = 20.0


async def test_success_with_path_parameters(httpbin: Any, transport: aio_request.Transport) -> None:
    response = await transport.send(
        yarl.URL(httpbin.url),
        aio_request.get("status/{status}", path_parameters={"status": "200"}),
        DEFAULT_TIMEOUT,
    )
    try:
        assert response.status == 200
    finally:
        await response.close()


async def test_json(httpbin: Any, transport: aio_request.Transport) -> None:
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


async def test_json_empty_response(httpbin: Any, transport: aio_request.Transport) -> None:
    response = await transport.send(
        yarl.URL(httpbin.url),
        aio_request.post("status/200"),
        DEFAULT_TIMEOUT,
    )
    try:
        assert response.status == 200
        assert await response.json(content_type=None) is None
        headers = response.headers
        assert headers == multidict.CIMultiDict[str](
            {
                "Date": unittest.mock.ANY,
                "Server": "Pytest-HTTPBIN/0.1.0",
                "Content-Type": "text/html; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "true",
                "Content-Length": "0",
                "Connection": "Close",
            }
        )
    finally:
        await response.close()


async def test_utf8_text(httpbin: Any, transport: aio_request.Transport) -> None:
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


async def test_success_with_query_parameters(httpbin: Any, transport: aio_request.Transport) -> None:
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


async def test_success_with_query_parameters_multidict(httpbin: Any, transport: aio_request.Transport) -> None:
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


async def test_redirects_max_redirects(httpbin: Any, transport: aio_request.Transport) -> None:
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


async def test_redirects_not_allowed(httpbin: Any, transport: aio_request.Transport) -> None:
    response = await transport.send(
        yarl.URL(f"{httpbin.url}/absolute-redirect/10"),
        aio_request.get("", allow_redirects=False),
        DEFAULT_TIMEOUT,
    )
    assert response.status == 302
    assert response.headers["Location"] == f"{httpbin.url}/absolute-redirect/9"


async def test_redirects_allowed_default(httpbin: Any, transport: aio_request.Transport) -> None:
    response = await transport.send(
        yarl.URL(f"{httpbin.url}/absolute-redirect/5"),
        aio_request.get(""),
        DEFAULT_TIMEOUT,
    )
    assert response.status == 200


async def test_connection_refused_retries_then_fails(
    transport: aio_request.Transport,
    unused_port: Callable[[], int],
    caplog: pytest.LogCaptureFixture,
) -> None:
    port = unused_port()

    with caplog.at_level(logging.DEBUG, logger="aio_request"):
        response = await transport.send(
            yarl.URL(f"http://127.0.0.1:{port}"),
            aio_request.get("test"),
            DEFAULT_TIMEOUT,
        )

    assert response.status == 489
    send_logs = [r for r in caplog.records if "Sending request" in r.message]
    assert len(send_logs) == 3


async def test_successful_request_no_retry(
    httpbin: Any,
    transport: aio_request.Transport,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="aio_request"):
        response = await transport.send(
            yarl.URL(httpbin.url),
            aio_request.get("get"),
            DEFAULT_TIMEOUT,
        )
    try:
        assert response.status == 200
        send_logs = [r for r in caplog.records if "Sending request" in r.message]
        assert len(send_logs) == 1
    finally:
        await response.close()


async def test_connection_reset_no_retry(
    transport: aio_request.Transport,
    caplog: pytest.LogCaptureFixture,
    unused_port: Callable[[], int],
    resetting_server_factory: Callable[[int], contextlib.AbstractAsyncContextManager],
) -> None:
    port = unused_port()
    async with resetting_server_factory(port):
        with caplog.at_level(logging.DEBUG, logger="aio_request"):
            response = await transport.send(
                yarl.URL(f"http://127.0.0.1:{port}"),
                aio_request.get("test"),
                DEFAULT_TIMEOUT,
            )

        assert response.status == 489
        send_logs = [r for r in caplog.records if "Sending request" in r.message]
        assert len(send_logs) == 1
