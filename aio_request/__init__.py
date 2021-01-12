__version__ = "0.0.2"

from .strategy import RequestStrategy  # noqa
from .base import Request, Response, ClosableResponse, EmptyResponse  # noqa
from .delays_provider import linear_delays, constant_delays  # noqa
from .request_sender import RequestSender  # noqa
from .response_classifier import ResponseVerdict, ResponseClassifier, DefaultResponseClassifier  # noqa
from .requests import get, post, put, delete, put_json, post_json  # noqa
from .strategy import RequestStrategy, RequestStrategiesFactory, MethodBasedStrategy  # noqa
from .deadline import Deadline  # noqa
