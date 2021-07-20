import multidict
import pytest

import aio_request


async def test_update_headers():
    request = aio_request.get("get", headers={"a": "b"})
    request = request.update_headers({"c": "d"})

    assert request.headers == {"a": "b", "c": "d"}


@pytest.mark.parametrize(
    "expected, response_content_type, content_type",
    [
        (False, "", "application/json"),
        (False, "application/xml", "application/json"),
        (True, "application/json", "application/json"),
        (True, "application/problem+json", "application/json"),
    ],
)
async def test_has_expected_content_type(expected: bool, response_content_type: str, content_type: str):
    headers = multidict.CIMultiDict[str]()
    headers.add(aio_request.Header.CONTENT_TYPE, response_content_type)
    response = aio_request.EmptyResponse(
        status=200,
        headers=multidict.CIMultiDictProxy[str](headers),
    )
    assert expected == aio_request.has_content_type(response, content_type=content_type)
