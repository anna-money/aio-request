import abc
import collections
import enum
import time
from typing import DefaultDict, Optional

import yarl


class CircuitState(str, enum.Enum):
    OPENED = "OPENED"
    HALF_OPENED = "HALF_OPENED"
    CLOSED = "CLOSED"


class CircuitBreakerMetricsSnapshot:
    __slots__ = ("started_at", "successes", "failures")

    def __init__(self, started_at: float, successes: int = 0, failures: int = 0) -> None:
        self.started_at = started_at
        self.successes = successes
        self.failures = failures


class CircuitBreakerMetrics(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def increment_successes(self) -> None:
        ...

    @abc.abstractmethod
    def increment_failures(self) -> None:
        ...

    @abc.abstractmethod
    def reset(self) -> None:
        ...

    @abc.abstractmethod
    def collect(self) -> CircuitBreakerMetricsSnapshot:
        ...


class RollingCircuitBreakerMetrics(CircuitBreakerMetrics):
    __slots__ = ("_window_duration", "_sampling_duration", "_last_n", "_current")

    def __init__(self, sampling_duration: float, windows_count: int) -> None:
        self._sampling_duration = sampling_duration
        self._window_duration = sampling_duration / windows_count
        self._last_n: collections.deque = collections.deque()  # type: ignore
        self._current: Optional[CircuitBreakerMetricsSnapshot] = None

    def increment_successes(self) -> None:
        self._refresh()
        self._current.successes += 1  # type: ignore

    def increment_failures(self) -> None:
        self._refresh()
        self._current.failures += 1  # type: ignore

    def reset(self) -> None:
        self._current = None
        self._last_n.clear()

    def collect(self) -> CircuitBreakerMetricsSnapshot:
        self._refresh()

        successes, failures = 0, 0
        for last in self._last_n:
            successes += last.successes
            failures += last.failures

        return CircuitBreakerMetricsSnapshot(self._last_n[0].started_at, successes, failures)

    def _refresh(self) -> None:
        now = time.time()
        if self._current is None or (now - self._current.started_at) >= self._window_duration:
            self._current = CircuitBreakerMetricsSnapshot(now)
            self._last_n.append(self._current)

        while self._last_n:
            last_state = self._last_n[0]
            if (now - last_state.started_at) < self._sampling_duration:
                break

            self._last_n.popleft()


class CircuitBreaker(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def on_execute(self, endpoint: yarl.URL) -> bool:
        ...

    @abc.abstractmethod
    def on_success(self, endpoint: yarl.URL) -> None:
        ...

    @abc.abstractmethod
    def on_failure(self, endpoint: yarl.URL) -> None:
        ...


class DefaultCircuitBreaker(CircuitBreaker):
    __slots__ = (
        "_block_duration",
        "_minimum_throughput",
        "_failure_threshold",
        "_per_endpoint_metrics",
        "_per_endpoint_state",
        "_per_endpoint_blocked_till",
    )

    def __init__(
        self,
        *,
        block_duration: float,
        sampling_duration: float,
        minimum_throughput: float,
        failure_threshold: float,
        windows_count: int = 10,
    ):
        self._block_duration = block_duration
        self._minimum_throughput = minimum_throughput
        self._failure_threshold = failure_threshold
        self._per_endpoint_metrics: DefaultDict[yarl.URL, CircuitBreakerMetrics] = collections.defaultdict(
            lambda: RollingCircuitBreakerMetrics(sampling_duration, windows_count)
        )
        self._per_endpoint_state: DefaultDict[yarl.URL, CircuitState] = collections.defaultdict(
            lambda: CircuitState.CLOSED
        )
        self._per_endpoint_blocked_till: DefaultDict[yarl.URL, float] = collections.defaultdict(float)

    def on_execute(self, endpoint: yarl.URL) -> bool:
        state = self._per_endpoint_state[endpoint]
        if state == CircuitState.CLOSED:
            return True

        blocked_till = self._per_endpoint_blocked_till[endpoint]
        now = time.time()
        if blocked_till > now:
            return False

        self._per_endpoint_blocked_till[endpoint] = now + self._block_duration
        self._per_endpoint_state[endpoint] = CircuitState.HALF_OPENED
        return True

    def on_success(self, endpoint: yarl.URL) -> None:
        state = self._per_endpoint_state[endpoint]
        if state == CircuitState.HALF_OPENED:
            self._close(endpoint)
        self._per_endpoint_metrics[endpoint].increment_successes()

    def on_failure(self, endpoint: yarl.URL) -> None:
        state = self._per_endpoint_state[endpoint]
        if state == CircuitState.CLOSED:
            self._increment_failures(endpoint)
            snapshot = self._collect_metrics(endpoint)
            throughput = float(snapshot.successes + snapshot.failures)
            if throughput >= self._minimum_throughput and (snapshot.failures / throughput >= self._failure_threshold):
                self._open(endpoint)
        elif state == CircuitState.OPENED:
            self._increment_failures(endpoint)
        else:
            self._open(endpoint)

    def _increment_failures(self, endpoint: yarl.URL) -> None:
        self._per_endpoint_metrics[endpoint].increment_failures()

    def _increment_successes(self, endpoint: yarl.URL) -> None:
        self._per_endpoint_metrics[endpoint].increment_successes()

    def _collect_metrics(self, endpoint: yarl.URL) -> CircuitBreakerMetricsSnapshot:
        return self._per_endpoint_metrics[endpoint].collect()

    def _close(self, endpoint: yarl.URL) -> None:
        self._per_endpoint_metrics[endpoint].reset()
        self._per_endpoint_state[endpoint] = CircuitState.CLOSED
        self._per_endpoint_blocked_till[endpoint] = 0

    def _open(self, endpoint: yarl.URL) -> None:
        self._per_endpoint_blocked_till[endpoint] = time.time() + self._block_duration
        self._per_endpoint_state[endpoint] = CircuitState.OPENED


class NoopCircuitBreaker(CircuitBreaker):
    __slots__ = ()

    def on_execute(self, endpoint: yarl.URL) -> bool:
        return True

    def on_success(self, endpoint: yarl.URL) -> None:
        pass

    def on_failure(self, endpoint: yarl.URL) -> None:
        pass


NOOP_CIRCUIT_BREAKER = NoopCircuitBreaker()
