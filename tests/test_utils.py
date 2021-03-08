from typing import Dict, Optional

import pytest
import yarl

from aio_request.utils import substitute_path_parameters, attempts


@pytest.mark.parametrize(
    "url, parameters, result",
    [
        (yarl.URL("do"), None, yarl.URL("do")),
        (yarl.URL("{a}/do"), {"a": "1"}, yarl.URL("1/do")),
        (yarl.URL("{a}/{b}"), {"a": "1", "b": "2"}, yarl.URL("1/2")),
        (yarl.URL("{a}/do?b=2"), {"a": "1"}, yarl.URL("1/do?b=2")),
        (yarl.URL("do/{a}"), {"a": "1"}, yarl.URL("do/1")),
        (yarl.URL("https://site.com/"), {}, yarl.URL("https://site.com/")),
        (yarl.URL("https://site.com/{a}"), {"a": "1"}, yarl.URL("https://site.com:443/1")),
    ],
)
def test_substitute_path_parameters(url: yarl.URL, parameters: Optional[Dict[str, str]], result: yarl.URL) -> None:
    assert substitute_path_parameters(url, parameters) == result


def test_fixed_attempts():
    assert list(attempts(3)) == [0, 1, 2]


def test_infinite_attempts():
    done = []
    for attempt in attempts(-1):
        if attempt == 42:
            break
        done.append(attempt)

    assert done == list(attempts(42))
