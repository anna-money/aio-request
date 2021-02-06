# flake8: noqa
__version__ = "0.0.8"

from .base import ClosableResponse, EmptyResponse, Request, Response
from .deadline import Deadline
from .delays_provider import constant_delays, linear_delays
from .priority import Priority
from .request_sender import RequestSender
from .requests import delete, get, post, post_json, put, put_json
from .response_classifier import DefaultResponseClassifier, ResponseClassifier, ResponseVerdict
from .strategy import MethodBasedStrategy, RequestStrategiesFactory, RequestStrategy
