# Deprecated

import abc


class MetricsProvider(abc.ABC):
    __slots__ = ()


class NoopMetricsProvider(MetricsProvider):
    __slots__ = ()


NOOP_METRICS_PROVIDER = NoopMetricsProvider()
