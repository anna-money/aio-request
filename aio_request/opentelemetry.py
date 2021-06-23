import contextlib
from typing import Iterable

import multidict
import opentelemetry.context as otel_ctx
import opentelemetry.propagate as otel_propagate
import opentelemetry.semconv.trace as otel_semconv_trace
import opentelemetry.trace as otel_trace
import yarl

from .base import Headers, Request, Response
from .tracing import Span, SpanKind, Tracer


class _OpenTelemetrySpan(Span):
    __slots__ = ("_span",)

    def __init__(self, span: otel_trace.Span):
        self._span = span

    def set_response_attrs(self, response: Response) -> None:
        if not self._span.is_recording():
            return

        self._span.set_status(otel_trace.Status(self.http_status_to_status_code(response.status)))
        self._span.set_attribute(otel_semconv_trace.SpanAttributes.HTTP_STATUS_CODE, response.status)

    def set_request_attrs(self, endpoint: yarl.URL, request: Request) -> None:
        if not self._span.is_recording():
            return

        self._span.set_attribute(otel_semconv_trace.SpanAttributes.HTTP_METHOD, request.method)
        self._span.set_attribute(otel_semconv_trace.SpanAttributes.HTTP_URL, str(endpoint))

    @staticmethod
    def http_status_to_status_code(status: int) -> otel_trace.StatusCode:
        if status < 100:
            return otel_trace.StatusCode.ERROR
        if status <= 299:
            return otel_trace.StatusCode.UNSET
        if status <= 399:
            return otel_trace.StatusCode.UNSET
        return otel_trace.StatusCode.ERROR


class OpenTelemetryTracer(Tracer):
    __slots__ = ("_tracer",)

    def __init__(self, trace_provider: otel_trace.TracerProvider):
        self._tracer = trace_provider.get_tracer("aio_request")

    def start_span(self, name: str, kind: SpanKind) -> contextlib.AbstractContextManager[Span]:
        return self._start_span(name, kind)

    def get_headers_to_propagate(self) -> Headers:
        headers = multidict.CIMultiDict[str]()
        otel_propagate.inject(headers)
        return headers

    def setup_context(self, headers: Headers) -> contextlib.AbstractContextManager[None]:
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
