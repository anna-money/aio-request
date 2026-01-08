import pytest
import yarl

from aio_request import patch_json, post_json, put_json, request_json


def test_request_json_with_bytes_data() -> None:
    raw_bytes = b'{"key": "value"}'
    req = request_json("POST", "api/test", raw_bytes)

    assert req.body == raw_bytes


def test_post_json_with_bytes_data() -> None:
    raw_bytes = b'{"key": "value"}'
    req = post_json("api/test", raw_bytes)

    assert req.body == raw_bytes


def test_put_json_with_bytes_data() -> None:
    raw_bytes = b'{"key": "value"}'
    req = put_json("api/test", raw_bytes)

    assert req.body == raw_bytes


def test_patch_json_with_bytes_data() -> None:
    raw_bytes = b'{"key": "value"}'
    req = patch_json("api/test", raw_bytes)

    assert req.body == raw_bytes


@pytest.mark.parametrize(
    "base, relative, actual",
    (
        ("http://service.com", "hello", "http://service.com/hello"),
        ("http://service.com/", "hello", "http://service.com/hello"),
        ("http://service.com", "api/hello", "http://service.com/api/hello"),
        ("http://service.com/", "api/hello", "http://service.com/api/hello"),
        ("http://service.com", "hello", "http://service.com/hello"),
        ("http://service.com/", "hello", "http://service.com/hello"),
        ("http://service.com", "api/hello", "http://service.com/api/hello"),
        ("http://service.com/", "api/hello", "http://service.com/api/hello"),
        ("https://service.com", "hello", "https://service.com/hello"),
        ("https://service.com/", "hello", "https://service.com/hello"),
        ("https://service.com", "api/hello", "https://service.com/api/hello"),
        ("https://service.com/", "api/hello", "https://service.com/api/hello"),
        ("https://service.com:12345", "hello", "https://service.com:12345/hello"),
        ("https://service.com:12345/", "hello", "https://service.com:12345/hello"),
        ("https://service.com:12345", "api/hello", "https://service.com:12345/api/hello"),
        ("https://service.com:12345/", "api/hello", "https://service.com:12345/api/hello"),
    ),
)
async def test_absolute(base: str, relative: str, actual: str) -> None:
    expected = yarl.URL(base).join(yarl.URL(relative))
    assert expected == yarl.URL(actual)
    assert expected.raw_path.startswith("/")
