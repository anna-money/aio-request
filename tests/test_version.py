import pytest

from aio_request import _parse_version  # pyright: ignore[reportPrivateUsage]


def test_alpha() -> None:
    assert _parse_version("0.1.2a2") == (0, 1, 2, "alpha", 2)
    assert _parse_version("1.2.3a") == (1, 2, 3, "alpha", 0)


def test_beta() -> None:
    assert _parse_version("0.1.2b2") == (0, 1, 2, "beta", 2)
    assert _parse_version("0.1.2b") == (0, 1, 2, "beta", 0)


def test_rc() -> None:
    assert _parse_version("0.1.2rc5") == (0, 1, 2, "candidate", 5)
    assert _parse_version("0.1.2rc") == (0, 1, 2, "candidate", 0)


def test_final() -> None:
    assert _parse_version("0.1.2") == (0, 1, 2, "final", 0)


def test_invalid() -> None:
    pytest.raises(ImportError, _parse_version, "0.1")
    pytest.raises(ImportError, _parse_version, "0.1.1.2")
    pytest.raises(ImportError, _parse_version, "0.1.1z2")
