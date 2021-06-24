import contextlib
from typing import ContextManager, Iterable, Optional

import multidict
import opentelemetry.context as otel_ctx
import opentelemetry.propagate as otel_propagate
import opentelemetry.semconv.trace as otel_semconv_trace
import opentelemetry.trace as otel_trace
import yarl

from .base import Headers
from .tracing import Span, SpanKind, Tracer


class _OpenTelemetrySpan(Span):
    __slots__ = ("_span",)

    def __init__(self, span: otel_trace.Span):
        self._span = span

    def set_response_status(self, status: int) -> None:
        if not self._span.is_recording():
            return

        self._span.set_status(otel_trace.Status(self.status_to_status_code(status)))
        self._span.set_attribute(otel_semconv_trace.SpanAttributes.HTTP_STATUS_CODE, status)

    def set_request_method(self, method: str) -> None:
        if not self._span.is_recording():
            return

        self._span.set_attribute(otel_semconv_trace.SpanAttributes.HTTP_METHOD, method)

    def set_request_endpoint(self, endpoint: yarl.URL) -> None:
        if not self._span.is_recording():
            return

        self._span.set_attribute(otel_semconv_trace.SpanAttributes.HTTP_HOST, str(endpoint))

    def set_request_path(self, path: yarl.URL) -> None:
        if not self._span.is_recording():
            return

        self._span.set_attribute(otel_semconv_trace.SpanAttributes.HTTP_TARGET, str(path))

    def set_request_route(self, route: str) -> None:
        if not self._span.is_recording():
            return

        self._span.set_attribute(otel_semconv_trace.SpanAttributes.HTTP_ROUTE, route)

    @staticmethod
    def status_to_status_code(status: int) -> otel_trace.StatusCode:
        if status < 100:
            return otel_trace.StatusCode.ERROR
        if status <= 299:
            return otel_trace.StatusCode.UNSET
        if status <= 399:
            return otel_trace.StatusCode.UNSET
        return otel_trace.StatusCode.ERROR


class OpenTelemetryTracer(Tracer):
    __slots__ = ("_tracer",)

    def __init__(self, trace_provider: Optional[otel_trace.TracerProvider] = None):
        self._tracer = (trace_provider or otel_trace.get_tracer_provider()).get_tracer("aio_request")

    def start_span(self, name: str, kind: SpanKind) -> ContextManager[Span]:
        return self._start_span(name, kind)

    def get_context_headers(self) -> Headers:
        headers = multidict.CIMultiDict[str]()
        otel_propagate.inject(headers)
        return headers

    def setup_context(self, headers: Headers) -> ContextManager[None]:
        return self._setup_context(headers)

    @contextlib.contextmanager  # type: ignore
    def _setup_context(self, headers: Headers) -> Iterable[None]:
        context = otel_propagate.extract(headers)
        token = otel_ctx.attach(context)
        try:
            yield
        finally:
            otel_ctx.detach(token)

    @contextlib.contextmanager  # type: ignore
    def _start_span(self, name: str, kind: SpanKind) -> Iterable[Span]:
        span_ctx = self._tracer.start_as_current_span(
            name=name, kind=otel_trace.SpanKind.CLIENT if kind == SpanKind.CLIENT else otel_trace.SpanKind.SERVER
        )
        with span_ctx as span:
            yield _OpenTelemetrySpan(span)
