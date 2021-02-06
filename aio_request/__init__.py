__version__ = "0.0.8"

from .base import ClosableResponse, EmptyResponse, Request, Response  # noqa
from .deadline import Deadline  # noqa
from .delays_provider import constant_delays, linear_delays  # noqa
from .priority import Priority  # noqa
from .request_sender import RequestSender  # noqa
from .requests import delete, get, post, post_json, put, put_json  # noqa
from .response_classifier import DefaultResponseClassifier, ResponseClassifier, ResponseVerdict  # noqa
from .strategy import RequestStrategy  # noqa
from .strategy import MethodBasedStrategy, RequestStrategiesFactory  # noqa
