# flake8: noqa
__version__ = "0.0.18"

from .base import ClosableResponse, EmptyResponse, Header, Method, Request, Response
from .client import Client, setup
from .context import get_context, set_context
from .deadline import Deadline
from .delays_provider import constant_delays, linear_delays
from .metrics import ClientMetricsCollector
from .priority import Priority
from .request_sender import RequestSender
from .requests import delete, get, post, post_json, put, put_json
from .response_classifier import DefaultResponseClassifier, ResponseClassifier, ResponseVerdict
from .strategy import MethodBasedStrategy, RequestStrategiesFactory, RequestStrategy

try:
    import aiohttp

    from .aiohttp import AioHttpRequestSender, aiohttp_middleware_factory
except ImportError:
    pass

try:
    import prometheus_client

    from .prometheus import PrometheusClientMetricsCollector
except ImportError:
    pass
