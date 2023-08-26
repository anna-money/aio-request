import pytest

import aio_request


@pytest.mark.parametrize(
    "status, verdict_for_status, verdict",
    [
        (408, None, aio_request.ResponseVerdict.REJECT),
        (400, None, aio_request.ResponseVerdict.ACCEPT),
        (429, None, aio_request.ResponseVerdict.REJECT),
        (429, {429: aio_request.ResponseVerdict.ACCEPT}, aio_request.ResponseVerdict.ACCEPT),
    ],
)
def test_default_response_classifier(
    status: int, verdict_for_status: dict[int, aio_request.ResponseVerdict], verdict: aio_request.ResponseVerdict
) -> None:
    classifier = aio_request.DefaultResponseClassifier(verdict_for_status=verdict_for_status)
    assert classifier.classify(aio_request.EmptyResponse(status=status)) == verdict
