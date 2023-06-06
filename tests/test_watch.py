import asyncio
from typing import List
import pytest

from etcetra import EtcdClient, WatchEvent, WatchEventType


@pytest.mark.asyncio
async def test_watch(etcd: EtcdClient):
    events: List[WatchEvent] = []

    async def _put_task():
        await asyncio.sleep(1)
        async with etcd.connect() as communicator:
            await communicator.put('/tmp/asd', 'fgh')
            await asyncio.sleep(0.5)
            await communicator.put('/tmp/qwe', 'rty')
            await asyncio.sleep(0.5)
            await communicator.delete('/tmp/qwe')

    async def _watch_task():
        async with etcd.connect() as communicator:
            async for event in communicator.watch_prefix('/tmp'):
                events.append(event)
        return events

    put_task = asyncio.create_task(_put_task())
    watch_task = asyncio.create_task(_watch_task())

    await asyncio.sleep(3)
    put_task.cancel()
    watch_task.cancel()

    assert events[0] == WatchEvent(
        key='/tmp/asd', value='fgh', prev_value=None, event=WatchEventType.PUT)
    assert events[1] == WatchEvent(
        key='/tmp/qwe', value='rty', prev_value=None, event=WatchEventType.PUT)
    assert events[2] == WatchEvent(
        key='/tmp/qwe', value='', prev_value=None, event=WatchEventType.DELETE)
    assert len(events) == 3
