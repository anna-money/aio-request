# aio-request

```python
import aiohttp

from aio_request import MethodBasedStrategy, RequestStrategiesFactory, get, post, Deadline
from aio_request.aiohttp import AioHttpRequestSender

client_session = aiohttp.ClientSession()
async with client_session:
    request_strategies_factory = RequestStrategiesFactory(
        AioHttpRequestSender("http://endpoint:8080", client_session)
    )
    request_strategy = MethodBasedStrategy(
        {
            "GET": request_strategies_factory.parallel(),
            "POST": request_strategies_factory.sequential()
        }
    )
    async with request_strategy.request(get("/thing"), deadline=Deadline.from_timeout(5)) as response:
        pass  # process response here

    async with request_strategy.request(post("/thing"), deadline=Deadline.from_timeout(5)) as response:
        pass  # process response here
```