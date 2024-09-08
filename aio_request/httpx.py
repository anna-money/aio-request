import collections.abc
import json
import logging
from typing import Any

import httpx
import multidict
import yarl

try:
    import cchardet  # type: ignore

    def detect_encoding(content: bytes) -> str | None:
        return cchardet.detect(content)["encoding"]

except ImportError:
    try:
        import charset_normalizer  # type: ignore

        def detect_encoding(content: bytes) -> str | None:
            return str(charset_normalizer.detect(content)["encoding"])

    except ImportError:

        def detect_encoding(content: bytes) -> str | None:
            return None


from .base import (
    EmptyResponse,
    Header,
    UnexpectedContentTypeError,
    build_query_parameters,
    is_expected_content_type,
    substitute_path_parameters,
)
from .request import Request
from .transport import ClosableResponse, Transport

logger = logging.getLogger(__package__)


class HttpxTransport(Transport):
    __slots__ = (
        "__client",
        "__buffer_payload",
        "__too_many_redirects_code",
        "__network_errors_code",
    )

    def __init__(
        self,
        client: httpx.AsyncClient,
        network_errors_code: int = 489,
        too_many_redirects_code: int = 488,
        buffer_payload: bool = True,
    ):
        self.__client = client
        self.__buffer_payload = buffer_payload
        self.__too_many_redirects_code = too_many_redirects_code
        self.__network_errors_code = network_errors_code

    async def send(self, endpoint: yarl.URL, request: Request, timeout: float) -> ClosableResponse:
        if not endpoint.is_absolute():
            raise RuntimeError("Base url should be absolute")

        method = request.method
        url = endpoint.join(substitute_path_parameters(request.url, request.path_parameters))
        if request.query_parameters is not None:
            url = url.update_query(build_query_parameters(request.query_parameters))
        headers = request.headers
        body = request.body
        allow_redirects = request.allow_redirects

        client_request = self.__client.build_request(
            method=method,
            url=httpx.URL(str(url)),
            content=body,
            headers=headers,
            timeout=timeout,
        )

        try:
            locations = []
            redirects = 0
            while True:
                client_response = await self.__client.send(client_request, follow_redirects=False)
                if client_response.next_request is not None and allow_redirects:
                    locations.extend(client_response.headers.get_list("Location"))
                    client_request = client_response.next_request
                    await client_response.aclose()

                    if redirects >= request.max_redirects - 1:
                        break

                    redirects += 1
                    continue

                if self.__buffer_payload:
                    await client_response.aread()
                return _HttpxResponse(client_response)

            headers = multidict.CIMultiDict[str]()
            for location in locations:
                headers.add(Header.LOCATION, location)
            return EmptyResponse(
                status=self.__too_many_redirects_code,
                headers=multidict.CIMultiDictProxy[str](headers),
            )

        except httpx.NetworkError:
            logger.warning(
                "Request %s %s has failed: network error",
                method,
                url,
                exc_info=True,
                extra={
                    "request_method": method,
                    "request_url": url,
                },
            )
            return EmptyResponse(status=self.__network_errors_code)


class _HttpxResponse(ClosableResponse):
    __slots__ = ("__response",)

    def __init__(self, response: httpx.Response):
        self.__response = response

    async def close(self) -> None:
        await self.__response.aclose()

    @property
    def status(self) -> int:
        return self.__response.status_code

    @property
    def headers(self) -> multidict.CIMultiDictProxy[str]:
        return multidict.CIMultiDictProxy[str](multidict.CIMultiDict[str](self.__response.headers.multi_items()))

    async def json(
        self,
        *,
        encoding: str | None = None,
        loads: collections.abc.Callable[[str], Any] = json.loads,
        content_type: str | None = "application/json",
    ) -> Any:
        if content_type is not None:
            response_content_type = self.__response.headers.get(Header.CONTENT_TYPE, "").lower()
            if not is_expected_content_type(response_content_type, content_type):
                raise UnexpectedContentTypeError(f"Expected {content_type}, actual {response_content_type}")

        return loads(await self.text(encoding=encoding))

    async def read(self) -> bytes:
        return await self.__response.aread()

    async def text(self, encoding: str | None = None) -> str:
        content = await self.__response.aread()
        return content.decode(encoding or self.__response.charset_encoding or detect_encoding(content) or "utf-8")
