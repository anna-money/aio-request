import pytest

import aio_request

from .conftest import MockPerfCounter


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"min_delay_seconds": -1}, "Delays must be non-negative"),
        ({"max_delay_seconds": -1}, "Delays must be non-negative"),
        ({"min_delay_seconds": 10, "max_delay_seconds": 1}, "min_delay must be less than or equal to max_delay"),
        ({"percentile": 0.0}, "percentile must be in"),
        ({"percentile": 1.0}, "percentile must be in"),
        ({"window_size_seconds": 0}, "window_size_seconds must be positive"),
        ({"buckets_count": 0}, "buckets_count must be positive"),
    ],
)
def test_validation(kwargs: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        aio_request.PercentileBasedRequestAttemptDelaysProvider(**kwargs)


def test_returns_min_delay_when_no_data() -> None:
    provider = aio_request.PercentileBasedRequestAttemptDelaysProvider(min_delay_seconds=0.1)
    assert provider(aio_request.get("test"), attempt=1) == 0.1


@pytest.mark.parametrize(
    "status,elapsed",
    [
        (500, 0.5),
        (200, -1),
    ],
)
def test_skips_unusable_responses(status: int, elapsed: float) -> None:
    provider = aio_request.PercentileBasedRequestAttemptDelaysProvider(min_delay_seconds=0.1)
    request = aio_request.get("test")

    provider.observe(request, aio_request.EmptyResponse(status=status, elapsed=elapsed))

    assert provider(request, attempt=1) == 0.1


def test_uses_observed_latency() -> None:
    provider = aio_request.PercentileBasedRequestAttemptDelaysProvider(
        percentile=0.5,
        min_delay_seconds=0.01,
        max_delay_seconds=100,
    )
    request = aio_request.get("test")

    provider.observe(request, aio_request.EmptyResponse(status=200, elapsed=1.0))

    assert provider(request, attempt=1) == 1.0
    assert provider(request, attempt=2) == 2.0
    assert provider(request, attempt=3) == 3.0


def test_clamps_to_min_delay() -> None:
    provider = aio_request.PercentileBasedRequestAttemptDelaysProvider(
        percentile=0.5,
        min_delay_seconds=0.5,
        max_delay_seconds=10,
    )
    request = aio_request.get("test")

    provider.observe(request, aio_request.EmptyResponse(status=200, elapsed=0.001))

    assert provider(request, attempt=1) == 0.5


def test_clamps_to_max_delay() -> None:
    provider = aio_request.PercentileBasedRequestAttemptDelaysProvider(
        percentile=0.5,
        min_delay_seconds=0.01,
        max_delay_seconds=0.5,
    )
    request = aio_request.get("test")

    provider.observe(request, aio_request.EmptyResponse(status=200, elapsed=10.0))

    assert provider(request, attempt=1) == 0.5
    assert provider(request, attempt=2) == 1.0


def test_tracks_by_method_and_url() -> None:
    provider = aio_request.PercentileBasedRequestAttemptDelaysProvider(
        percentile=0.5,
        min_delay_seconds=0.01,
        max_delay_seconds=100,
    )

    get_request = aio_request.get("endpoint")
    post_request = aio_request.post("endpoint")
    other_request = aio_request.get("other")

    provider.observe(get_request, aio_request.EmptyResponse(status=200, elapsed=1.0))
    provider.observe(post_request, aio_request.EmptyResponse(status=200, elapsed=2.0))
    provider.observe(other_request, aio_request.EmptyResponse(status=200, elapsed=3.0))

    assert provider(get_request, attempt=1) == 1.0
    assert provider(post_request, attempt=1) == 2.0
    assert provider(other_request, attempt=1) == 3.0


def test_buckets_expire(mock_perf_counter: MockPerfCounter) -> None:
    provider = aio_request.PercentileBasedRequestAttemptDelaysProvider(
        percentile=0.5,
        min_delay_seconds=0.05,
        max_delay_seconds=100,
        window_size_seconds=1.0,
        buckets_count=2,
    )
    request = aio_request.get("test")

    mock_perf_counter.value = 1000.0
    provider.observe(request, aio_request.EmptyResponse(status=200, elapsed=1.0))

    mock_perf_counter.value = 1000.5
    assert provider(request, attempt=1) == 1.0

    mock_perf_counter.value = 1002.0
    assert provider(request, attempt=1) == 0.05


def test_empty_response_elapsed() -> None:
    assert aio_request.EmptyResponse(status=200, elapsed=0.5).elapsed == 0.5
    assert aio_request.EmptyResponse(status=200).elapsed == 0
