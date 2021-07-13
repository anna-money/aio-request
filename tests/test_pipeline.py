import pytest
import yarl

import aio_request


class NextPassingModule(aio_request.RequestModule):
    __slots__ = ()

    async def execute(
        self,
        next: aio_request.NextModuleFunc,
        *,
        endpoint: yarl.URL,
        request: aio_request.Request,
        deadline: aio_request.Deadline,
        priority: aio_request.Priority
    ) -> aio_request.ClosableResponse:
        return await next(endpoint, request, deadline, priority)


class RejectingModule(aio_request.RequestModule):
    __slots__ = ()

    async def execute(
        self,
        next: aio_request.NextModuleFunc,
        *,
        endpoint: yarl.URL,
        request: aio_request.Request,
        deadline: aio_request.Deadline,
        priority: aio_request.Priority
    ) -> aio_request.ClosableResponse:
        return aio_request.EmptyResponse(status=500)


class ResponseModule(aio_request.RequestModule):
    __slots__ = ()

    async def execute(
        self,
        next: aio_request.NextModuleFunc,
        *,
        endpoint: yarl.URL,
        request: aio_request.Request,
        deadline: aio_request.Deadline,
        priority: aio_request.Priority
    ) -> aio_request.ClosableResponse:
        return aio_request.EmptyResponse(status=200)


async def test_build_pipeline_exception():
    pipeline = aio_request.build_pipeline([])
    with pytest.raises(NotImplementedError):
        await pipeline(
            yarl.URL("http://www.google.ru"),
            aio_request.get("search"),
            aio_request.Deadline.from_timeout(5),
            aio_request.Priority.HIGH,
        )


async def test_build_pipeline_last_module_should_not_use_next():
    pipeline = aio_request.build_pipeline([NextPassingModule()])
    with pytest.raises(NotImplementedError):
        await pipeline(
            yarl.URL("http://www.google.ru"),
            aio_request.get("search"),
            aio_request.Deadline.from_timeout(5),
            aio_request.Priority.HIGH,
        )


async def test_build_pipeline_last_module_should_return_response():
    pipeline = aio_request.build_pipeline([ResponseModule()])

    response = await pipeline(
        yarl.URL("http://www.google.ru"),
        aio_request.get("search"),
        aio_request.Deadline.from_timeout(5),
        aio_request.Priority.HIGH,
    )
    assert response.status == 200


async def test_build_pipeline_earliest_module_should_reject():
    pipeline = aio_request.build_pipeline([RejectingModule(), ResponseModule()])

    response = await pipeline(
        yarl.URL("http://www.google.ru"),
        aio_request.get("search"),
        aio_request.Deadline.from_timeout(5),
        aio_request.Priority.HIGH,
    )
    assert response.status == 500


async def test_build_pipeline_earliest_module_should_pass():
    pipeline = aio_request.build_pipeline([NextPassingModule(), ResponseModule()])

    response = await pipeline(
        yarl.URL("http://www.google.ru"),
        aio_request.get("search"),
        aio_request.Deadline.from_timeout(5),
        aio_request.Priority.HIGH,
    )
    assert response.status == 200
