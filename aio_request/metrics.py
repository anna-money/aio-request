import abc
from typing import Any, Dict


class MetricsProvider(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def increment_counter(self, name: str, tags: Dict[str, Any], value: float = 1) -> None:
        pass

    @abc.abstractmethod
    def observe_value(self, name: str, tags: Dict[str, Any], value: float) -> None:
        pass


class NoopMetricsProvider(MetricsProvider):
    __slots__ = ()

    def increment_counter(self, name: str, tags: Dict[str, Any], value: float = 1) -> None:
        pass

    def observe_value(self, name: str, tags: Dict[str, Any], value: float) -> None:
        pass


NOOP_METRICS_PROVIDER = NoopMetricsProvider()
