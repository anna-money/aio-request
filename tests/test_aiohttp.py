import aio_request


async def test_success(request_strategies_factory):
    deadline = aio_request.Deadline.from_timeout(1.5)
    async with request_strategies_factory.sequential().request(aio_request.get("get?delay=1"), deadline) as response:
        assert response.status == 200


async def test_not_enough_timeout(request_strategies_factory):
    deadline = aio_request.Deadline.from_timeout(0.5)
    async with request_strategies_factory.sequential().request(aio_request.get("get?delay=1"), deadline) as response:
        assert response.status == 408


async def test_expired_budget(request_strategies_factory):
    deadline = aio_request.Deadline.from_timeout(0)
    async with request_strategies_factory.sequential().request(aio_request.get("get?delay=1"), deadline) as response:
        assert response.status == 408


async def test_low_timeout_threshold(request_strategies_factory):
    deadline = aio_request.Deadline.from_timeout(0.005)
    async with request_strategies_factory.sequential().request(aio_request.get("get?delay=1"), deadline) as response:
        assert response.status == 408
