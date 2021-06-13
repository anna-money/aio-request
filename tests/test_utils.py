import uuid
from typing import Dict, List, Optional, Union

import pytest
import yarl

from aio_request.base import QueryParameters, build_query_parameters, substitute_path_parameters


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


sample_uuid = uuid.uuid4()


@pytest.mark.parametrize(
    "query_parameters, expected_parameters",
    [
        ({}, {}),
        ({"a": None}, {}),
        ({"a": "b"}, {"a": "b"}),
        ({"a": 1}, {"a": "1"}),
        ({"a": True}, {"a": "True"}),
        ({"a": sample_uuid}, {"a": str(sample_uuid)}),
        ({"a": []}, {}),
        ({"a": [None]}, {}),
        ({"a": ["b", "c"]}, {"a": ["b", "c"]}),
        ({"a": [1, True, None]}, {"a": ["1", "True"]}),
    ],
)
def test_build_query_parameters(
    query_parameters: QueryParameters, expected_parameters: Dict[str, Union[str, List[str]]]
) -> None:
    assert build_query_parameters(query_parameters) == expected_parameters
    assert build_query_parameters(query_parameters.items()) == expected_parameters
