import asyncio
import socket
import unittest.mock

import aiohttp.abc

import aio_request


async def test_multiple_resolve() -> None:
    base_resolver = unittest.mock.MagicMock(spec=aiohttp.abc.AbstractResolver)
    base_resolver.resolve.side_effect = [[{"endpoint": {"ip": "1"}}], [{"endpoint": {"ip": "2"}}]]
    resolver = aio_request.AioHttpDnsResolver(base_resolver, interval=0.5)
    try:
        first = await resolver.resolve("host", 80, socket.AF_INET)
        second = await resolver.resolve("host", 80, socket.AF_INET)
    finally:
        await resolver.close()

    base_resolver.resolve.assert_called_once_with("host", 80, socket.AF_INET)
    base_resolver.close.assert_called_once()

    assert first == [{"endpoint": {"ip": "1"}}]
    assert second == [{"endpoint": {"ip": "1"}}]


async def test_resolve_in_background() -> None:
    base_resolver = unittest.mock.MagicMock(spec=aiohttp.abc.AbstractResolver)
    base_resolver.resolve.side_effect = [[{"endpoint": {"ip": "1"}}], [{"endpoint": {"ip": "2"}}]]
    resolver = aio_request.AioHttpDnsResolver(base_resolver, interval=0.5)
    try:
        first = await resolver.resolve("host", 80, socket.AF_INET)
        await asyncio.sleep(0.7)
        second = await resolver.resolve("host", 80, socket.AF_INET)
    finally:
        await resolver.close()

    base_resolver.resolve.assert_called_with("host", 80, socket.AF_INET)
    base_resolver.close.assert_called_once()

    assert first == [{"endpoint": {"ip": "1"}}]
    assert second == [{"endpoint": {"ip": "2"}}]


async def test_resolve_failures_in_background() -> None:
    base_resolver = unittest.mock.MagicMock(spec=aiohttp.abc.AbstractResolver)
    base_resolver.resolve.side_effect = [
        [{"endpoint": {"ip": "1"}}],
        Exception("Failure"),
        Exception("Failure"),
        Exception("Failure"),
        [{"endpoint": {"ip": "2"}}],
    ]
    resolver = aio_request.AioHttpDnsResolver(base_resolver, interval=0.5)
    try:
        first = await resolver.resolve("host", 80, socket.AF_INET)
        await asyncio.sleep(2)
        second = resolver.resolve_no_wait("host", 80, socket.AF_INET)
    finally:
        await resolver.close()

    base_resolver.resolve.assert_called_with("host", 80, socket.AF_INET)
    assert base_resolver.resolve.call_count == 4
    base_resolver.close.assert_called_once()

    assert first == [{"endpoint": {"ip": "1"}}]
    assert second is None
