import multidict
import pytest

import aio_request


async def test_update_headers() -> None:
    request = aio_request.get("get", headers={"a": "b", "x": "y"})
    request = request.update_headers({"c": "d", "x": "z"})

    assert request.headers == {"a": "b", "c": "d", "x": "z"}


async def test_extend_headers() -> None:
    request = aio_request.get("get", headers={"a": "b", "x": "y"})
    request = request.extend_headers({"c": "d", "x": "z"})

    assert request.headers == multidict.CIMultiDict([("a", "b"), ("x", "y"), ("c", "d"), ("x", "z")])


@pytest.mark.parametrize(
    "is_json, response_content_type, content_type",
    [
        (False, "", "application/json"),
        (False, "application/xml", "application/json"),
        (True, "application/json", "application/json"),
        (True, "application/problem+json", "application/json"),
        (True, "application/json;charset=uft-8", "application/json"),
        (True, "application/problem+json;charset=uft-8", "application/json"),
    ],
)
async def test_response_is_json(is_json: bool, response_content_type: str, content_type: str) -> None:
    headers = multidict.CIMultiDict[str]()
    headers.add(aio_request.Header.CONTENT_TYPE, response_content_type)
    response = aio_request.EmptyResponse(
        status=200,
        headers=multidict.CIMultiDictProxy[str](headers),
    )
    assert is_json == response.is_json
