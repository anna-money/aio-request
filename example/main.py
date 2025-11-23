import asyncio

import aiohttp.web
import aiohttp.web_response
import prometheus_client as prom
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import set_tracer_provider

import aio_request

resource = Resource(attributes={"service.name": "example"})

prometheus_metrics_reader = PrometheusMetricReader()
set_meter_provider(MeterProvider(metric_readers=[prometheus_metrics_reader], resource=resource))

set_tracer_provider(
    TracerProvider(
        active_span_processor=BatchSpanProcessor(ConsoleSpanExporter("example")),
        resource=resource,  # type: ignore
    )
)

AioHttpClientInstrumentor().instrument()

routes = aiohttp.web.RouteTableDef()


@routes.get("/")
async def hello(request: aiohttp.web_request.Request) -> aiohttp.web_response.Response:
    client = request.app["client"]
    async with client.request(aio_request.get("get")) as response:
        return aiohttp.web.Response(text=str(response.status))


@routes.get("/metrics")
async def metrics(request: aiohttp.web_request.Request) -> aiohttp.web_response.Response:
    return aiohttp.web_response.Response(
        body=await asyncio.get_running_loop().run_in_executor(None, prom.generate_latest), content_type="text/plain"
    )


async def create_app() -> aiohttp.web.Application:
    async def set_up_aio_request(app: aiohttp.web.Application) -> None:
        client_session = aiohttp.ClientSession()
        client = aio_request.setup(
            transport=aio_request.AioHttpTransport(client_session), endpoint="https://httpbin.org"
        )
        app["client"] = client
        yield
        await client_session.close()

    app = aiohttp.web.Application(middlewares=[aio_request.aiohttp_middleware_factory()])
    app.cleanup_ctx.append(set_up_aio_request)
    app.add_routes(routes)

    return app


aiohttp.web.run_app(create_app())
