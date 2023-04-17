import aiohttp.web
import pytest
import yarl

import aio_request


@pytest.fixture
def redirects_app():
    redirects = [
        aiohttp.web.HTTPMovedPermanently("/redirect2"),
        aiohttp.web.HTTPMovedPermanently("/redirect1"),
        aiohttp.web.HTTPMovedPermanently("/"),
    ]

    async def root(request: aiohttp.web.Request) -> aiohttp.web.Response:
        return aiohttp.web.Response(body="root")

    async def redirect(request: aiohttp.web.Request) -> None:
        raise redirects.pop(0)

    app = aiohttp.web.Application()
    app.router.add_get("", root)
    app.router.add_get("/redirect1", redirect)
    app.router.add_get("/redirect2", redirect)
    app.router.add_get("/redirect3", redirect)
    return app


async def test_redirects_allowed_default(aiohttp_server, redirects_app):
    app = redirects_app()
    server = await aiohttp_server(app)
    async with aiohttp.ClientSession() as client_session:
        transport = aio_request.AioHttpTransport(client_session)
        response = await transport.send(
            yarl.URL(f"http://{server.host}:{server.port}/redirect3"),
            aio_request.get(""),
            5,
        )
        assert response.status == 200
        response_text = await response.text()
        assert response_text == "root"


async def test_redirects_not_allowed(aiohttp_server, redirects_app):
    app = redirects_app()
    server = await aiohttp_server(app)
    async with aiohttp.ClientSession() as client_session:
        transport = aio_request.AioHttpTransport(client_session)
        response = await transport.send(
            yarl.URL(f"http://{server.host}:{server.port}/redirect3"),
            aio_request.get("", allow_redirects=False),
            5,
        )
        assert response.status == 301
        assert response.headers["Location"] == "/redirect2"


async def test_redirects_max_redirects(aiohttp_server, redirects_app):
    app = redirects_app()
    server = await aiohttp_server(app)
    async with aiohttp.ClientSession() as client_session:
        transport = aio_request.AioHttpTransport(client_session)
        with pytest.raises(aio_request.TooManyRedirects):
            await transport.send(
                yarl.URL(f"http://{server.host}:{server.port}/redirect3"),
                aio_request.get("", allow_redirects=True, max_redirects=2),
                5,
            )
