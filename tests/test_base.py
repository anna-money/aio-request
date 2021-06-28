import aio_request


async def test_update_headers():
    request = aio_request.get("get", headers={"a": "b"})
    request = request.update_headers({"c": "d"})

    assert request.headers == {"a": "b", "c": "d"}
