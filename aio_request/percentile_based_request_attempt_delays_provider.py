import collections
import dataclasses

import tdigest

from .base import Request, Response
from .request_attempt_delays_provider import RequestAttemptDelaysProvider
from .request_response_observer import RequestResponseObserver
from .utils import perf_counter


class PercentileBasedRequestAttemptDelaysProvider(RequestAttemptDelaysProvider, RequestResponseObserver):
    __slots__ = (
        "__bucket_size_seconds",
        "__bucket_ttl",
        "__max_delay_seconds",
        "__metrics_by_endpoint",
        "__min_delay_seconds",
        "__percentile",
    )

    def __init__(
        self,
        *,
        percentile: float = 0.95,
        min_delay_seconds: float = 0.050,
        max_delay_seconds: float = 10,
        window_size_seconds: float = 5 * 60,
        buckets_count: int = 2,
    ):
        if min_delay_seconds < 0 or max_delay_seconds < 0:
            raise ValueError("Delays must be non-negative")
        if min_delay_seconds > max_delay_seconds:
            raise ValueError("min_delay must be less than or equal to max_delay")
        if not (0.0 < percentile < 1.0):
            raise ValueError("percentile must be in (0.0, 1.0)")
        if window_size_seconds <= 0:
            raise ValueError("window_size_seconds must be positive")
        if buckets_count <= 0:
            raise ValueError("buckets_count must be positive")

        self.__bucket_size_seconds = window_size_seconds / buckets_count
        self.__bucket_ttl = window_size_seconds + self.__bucket_size_seconds
        self.__percentile = percentile * 100
        self.__max_delay_seconds = max_delay_seconds
        self.__min_delay_seconds = min_delay_seconds
        self.__metrics_by_endpoint = collections.defaultdict(collections.deque)

    def __call__(self, request: Request, attempt: int) -> float:
        key = (request.method, request.url)
        buckets = self.__metrics_by_endpoint[key]
        now = perf_counter()
        while buckets and (now - buckets[0].started_at) > self.__bucket_ttl:
            buckets.popleft()

        if not buckets:
            return self.__min_delay_seconds

        oldest_bucket = buckets[0]
        per_attempt_delay = min(
            self.__max_delay_seconds, max(self.__min_delay_seconds, oldest_bucket.digest.percentile(self.__percentile))
        )
        return per_attempt_delay * attempt

    def observe(self, request: Request, response: Response) -> None:
        if response.elapsed < 0:
            return
        if not response.is_successful():
            return

        key = (request.method, request.url)
        buckets = self.__metrics_by_endpoint[key]
        now = perf_counter()

        while buckets and (now - buckets[0].started_at) > self.__bucket_ttl:
            buckets.popleft()

        if not buckets or (now - buckets[-1].started_at) >= self.__bucket_size_seconds:
            buckets.append(
                _DigestBucket(
                    started_at=now,
                    digest=tdigest.TDigest(),
                )
            )

        for bucket in buckets:
            bucket.digest.update(response.elapsed)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _DigestBucket:
    started_at: float
    digest: tdigest.TDigest
