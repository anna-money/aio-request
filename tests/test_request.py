import pytest
import yarl


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
