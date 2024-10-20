import abc
import collections
import collections.abc
import dataclasses
import enum
import time
from typing import Generic, TypeVar


class CircuitState(enum.StrEnum):
    OPEN = enum.auto()
    HALF_OPEN = enum.auto()
    CLOSED = enum.auto()


@dataclasses.dataclass(slots=True, kw_only=True)
class CircuitBreakerMetricsSnapshot:
    started_at: float
    successes: int = 0
    failures: int = 0


class CircuitBreakerMetrics(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def increment_successes(self) -> None: ...

    @abc.abstractmethod
    def increment_failures(self) -> None: ...

    @abc.abstractmethod
    def reset(self) -> None: ...

    @abc.abstractmethod
    def collect(self) -> CircuitBreakerMetricsSnapshot: ...


class RollingCircuitBreakerMetrics(CircuitBreakerMetrics):
    __slots__ = ("_window_duration", "_sampling_duration", "_last_n", "_current")

    def __init__(self, sampling_duration: float, windows_count: int) -> None:
        self._sampling_duration = sampling_duration
        self._window_duration = sampling_duration / windows_count
        self._last_n: collections.deque = collections.deque()  # type: ignore
        self._current: CircuitBreakerMetricsSnapshot | None = None

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

        return CircuitBreakerMetricsSnapshot(
            started_at=self._last_n[0].started_at, successes=successes, failures=failures
        )

    def _refresh(self) -> None:
        now = time.time()
        if self._current is None or (now - self._current.started_at) >= self._window_duration:
            self._current = CircuitBreakerMetricsSnapshot(started_at=now)
            self._last_n.append(self._current)

        while self._last_n:
            last_state = self._last_n[0]
            if (now - last_state.started_at) < self._sampling_duration:
                break

            self._last_n.popleft()


TScope = TypeVar("TScope")
TResult = TypeVar("TResult")


class CircuitBreaker(Generic[TScope, TResult], abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def execute(
        self,
        *,
        scope: TScope,
        operation: collections.abc.Callable[[], collections.abc.Awaitable[TResult]],
        fallback: TResult,
        is_successful: collections.abc.Callable[[TResult], bool],
    ) -> TResult: ...

    @property
    @abc.abstractmethod
    def state(self) -> collections.abc.Mapping[TScope, CircuitState]: ...


class DefaultCircuitBreaker(CircuitBreaker[TScope, TResult]):
    __slots__ = (
        "__break_duration",
        "__minimum_throughput",
        "__failure_threshold",
        "__per_scope_metrics",
        "__per_scope_state",
        "__per_scope_blocked_till",
    )

    def __init__(
        self,
        *,
        break_duration: float,
        failure_threshold: float,
        minimum_throughput: int,
        sampling_duration: float,
        windows_count: int = 10,
    ):
        """
        failure_threshold: The failure threshold at which the circuit will break (a number between 0 and 1)
        break_duration: The duration the circuit will stay open before resetting
        minimum_throughput: How many actions must pass through the circuit breaker to come into action
        sampling_duration: The duration when failure ratios are assessed
        """
        if break_duration <= 0:
            raise RuntimeError("Break duration should be positive")
        if minimum_throughput <= 0:
            raise RuntimeError("Minimum throughput should be positive")
        if failure_threshold <= 0 or failure_threshold >= 1:
            raise RuntimeError("Failure threshold should be between 0 and 1")
        if sampling_duration <= 0:
            raise RuntimeError("Sample duration should be positive")
        if windows_count <= 0:
            raise RuntimeError("Windows count should be positive")

        self.__break_duration = break_duration
        self.__minimum_throughput = minimum_throughput
        self.__failure_threshold = failure_threshold
        self.__per_scope_metrics = collections.defaultdict[TScope, CircuitBreakerMetrics](
            lambda: RollingCircuitBreakerMetrics(sampling_duration, windows_count)
        )
        self.__per_scope_state = collections.defaultdict[TScope, CircuitState](lambda: CircuitState.CLOSED)
        self.__per_scope_blocked_till = collections.defaultdict[TScope, float](float)

    async def execute(
        self,
        *,
        scope: TScope,
        operation: collections.abc.Callable[[], collections.abc.Awaitable[TResult]],
        fallback: TResult,
        is_successful: collections.abc.Callable[[TResult], bool],
    ) -> TResult:
        if not self._is_executable(scope):
            return fallback

        result = await operation()

        if is_successful(result):
            self._on_success(scope)
        else:
            self._on_failure(scope)

        return result

    @property
    def state(self) -> collections.abc.Mapping[TScope, CircuitState]:
        return dict(self.__per_scope_state)

    def _is_executable(self, scope: TScope) -> bool:
        state = self.__per_scope_state[scope]
        if state == CircuitState.CLOSED:
            return True

        blocked_till = self.__per_scope_blocked_till[scope]
        now = time.time()
        if blocked_till > now:
            return False

        # Only one operation should win and be executed
        self.__per_scope_blocked_till[scope] = now + self.__break_duration
        self.__per_scope_state[scope] = CircuitState.HALF_OPEN
        return True

    def _on_success(self, scope: TScope) -> None:
        state = self.__per_scope_state[scope]
        if state == CircuitState.HALF_OPEN:
            self._close(scope)
        self.__per_scope_metrics[scope].increment_successes()

    def _on_failure(self, scope: TScope) -> None:
        state = self.__per_scope_state[scope]
        if state == CircuitState.CLOSED:
            self._increment_failures(scope)
            snapshot = self._collect_metrics(scope)
            throughput = float(snapshot.successes + snapshot.failures)
            if throughput >= self.__minimum_throughput and (snapshot.failures / throughput >= self.__failure_threshold):
                self._open(scope)
        elif state == CircuitState.OPEN:
            self._increment_failures(scope)
        else:
            self._open(scope)

    def _increment_failures(self, scope: TScope) -> None:
        self.__per_scope_metrics[scope].increment_failures()

    def _increment_successes(self, scope: TScope) -> None:
        self.__per_scope_metrics[scope].increment_successes()

    def _collect_metrics(self, scope: TScope) -> CircuitBreakerMetricsSnapshot:
        return self.__per_scope_metrics[scope].collect()

    def _close(self, scope: TScope) -> None:
        self.__per_scope_metrics[scope].reset()
        self.__per_scope_state[scope] = CircuitState.CLOSED
        self.__per_scope_blocked_till[scope] = 0

    def _open(self, scope: TScope) -> None:
        self.__per_scope_blocked_till[scope] = time.time() + self.__break_duration
        self.__per_scope_state[scope] = CircuitState.OPEN


class NoopCircuitBreaker(CircuitBreaker[TScope, TResult]):
    __slots__ = ()

    async def execute(
        self,
        *,
        scope: TScope,
        operation: collections.abc.Callable[[], collections.abc.Awaitable[TResult]],
        fallback: TResult,
        is_successful: collections.abc.Callable[[TResult], bool],
    ) -> TResult:
        return await operation()

    @property
    def state(self) -> collections.abc.Mapping[TScope, CircuitState]:
        return {}
