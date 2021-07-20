import multidict
import pytest

import aio_request


async def test_update_headers():
    request = aio_request.get("get", headers={"a": "b"})
    request = request.update_headers({"c": "d"})

    assert request.headers == {"a": "b", "c": "d"}


@pytest.mark.parametrize(
    "is_json, response_content_type, content_type",
    [
        (False, "", "application/json"),
        (False, "application/xml", "application/json"),
        (True, "application/json", "application/json"),
        (True, "application/problem+json", "application/json"),
    ],
)
async def test_response_is_json(is_json: bool, response_content_type: str, content_type: str):
    headers = multidict.CIMultiDict[str]()
    headers.add(aio_request.Header.CONTENT_TYPE, response_content_type)
    response = aio_request.EmptyResponse(
        status=200, headers=multidict.CIMultiDictProxy[str](headers),
    )
    assert is_json == response.is_json
