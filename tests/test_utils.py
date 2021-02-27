from typing import Dict, Optional

import pytest
import yarl

from aio_request.utils import substitute_path_parameters


@pytest.mark.parametrize(
    "url, parameters, result",
    [
        (yarl.URL("do"), None, yarl.URL("do")),
        (yarl.URL("{a}/do"), {"a": "1"}, yarl.URL("1/do")),
        (yarl.URL("{a}/{b}"), {"a": "1", "b": "2"}, yarl.URL("1/2")),
        (yarl.URL("{a}/do?b=2"), {"a": "1"}, yarl.URL("1/do?b=2")),
    ],
)
def test_substitute_path_parameters(url: yarl.URL, parameters: Optional[Dict[str, str]], result: yarl.URL) -> None:
    assert substitute_path_parameters(url, parameters) == result
