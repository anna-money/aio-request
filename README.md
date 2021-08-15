# aio-request

This library simplifies an interaction between microservices:
1. Allows sending requests using various strategies
1. Propagates a deadline and a priority of requests
1. Exposes client/server metrics

Example:
```python
import aiohttp
import aio_request

async with aiohttp.ClientSession() as client_session:
    client = aio_request.setup(
        transport=aio_request.AioHttpTransport(client_session),
        endpoint="http://endpoint:8080/",
    )
    response_ctx = client.request(
        aio_request.get("thing"),
        deadline=aio_request.Deadline.from_timeout(5)
    )
    async with response_ctx as response:
        pass  # process response here
```

# Request strategies 
The following strategies are supported:
1. Single attempt. Only one attempt is sent.
1. Sequential. Attempts are sent sequentially with delays between them.
1. Parallel. Attempts are sent in parallel one by one with delays between them.

Attempts count and delays are configurable.

Example:
```python
import aiohttp
import aio_request

async with aiohttp.ClientSession() as client_session:
    client = aio_request.setup(
        transport=aio_request.AioHttpTransport(client_session),
        endpoint="http://endpoint:8080/",
    )
    response_ctx = client.request(
        aio_request.get("thing"),
        deadline=aio_request.Deadline.from_timeout(5),
        strategy=aio_request.parallel_strategy(
            attempts_count=3,
            delays_provider=aio_request.linear_delays(min_delay_seconds=0.1, delay_multiplier=0.1)
        )
    )
    async with response_ctx as response:
        pass  # process response here
```

# Deadline & priority propagation

To enable it for the server side a middleware should be configured:
```python
import aiohttp.web
import aio_request

app = aiohttp.web.Application(middlewares=[aio_request.aiohttp_middleware_factory()])
```

# Expose client/server metrics

To enable client metrics a metrics provider should be passed to the transport:
```python
import aiohttp
import aio_request

async with aiohttp.ClientSession() as client_session:
    client = aio_request.setup(
        transport=aio_request.AioHttpTransport(
            client_session,
            metrics_provider=aio_request.PROMETHEUS_METRICS_PROVIDER
        ),
        endpoint="http://endpoint:8080/",
    )
```

It is an example of how it should be done for aiohttp and prometheus.

To enable client metrics a metrics provider should be passed to the middleware:
```python
import aiohttp.web
import aio_request

app = aiohttp.web.Application(
    middlewares=[
        aio_request.aiohttp_middleware_factory(
            metrics_provider=aio_request.PROMETHEUS_METRICS_PROVIDER
        )
    ]
)
```

# Circuit breaker

```python
import aiohttp
import aio_request

async with aiohttp.ClientSession() as client_session:
    client = aio_request.setup_v2(
        transport=aio_request.AioHttpTransport(client_session),
        endpoint="http://endpoint:8080/",
        circuit_breaker=aio_request.DefaultCircuitBreaker[str, int](
            break_duration=1.0,
            sampling_duration=1.0,
            minimum_throughput=2,
            failure_threshold=0.5,
        ),
    )
```

In the case of requests count >= minimum throughput(>=2) in sampling period(1 second) the circuit breaker will open
if failed requests count/total requests count >= failure threshold(50%).
