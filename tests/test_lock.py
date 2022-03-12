import asyncio
from queue import Queue
import pytest

from etcetra import EtcdClient


@pytest.mark.asyncio
async def test_lock(etcd: EtcdClient):
    queue: Queue[int] = Queue()

    async def _lock_task_1(queue: Queue[int]):
        global lock_1_entered
        async with etcd.with_lock('/test/locka'):
            queue.put(1)
            await asyncio.sleep(10)

    async def _lock_task_2(queue: Queue[int]):
        global lock_2_entered
        await asyncio.sleep(3)
        async with etcd.with_lock('/test/locka'):
            queue.put(2)
            await asyncio.sleep(10)

    async def _lock_task_3(queue: Queue[int]):
        global lock_3_entered
        await asyncio.sleep(3)
        async with etcd.with_lock('/test/lockb'):
            queue.put(3)
            await asyncio.sleep(10)

    task_1 = asyncio.create_task(_lock_task_1(queue))
    task_2 = asyncio.create_task(_lock_task_2(queue))
    task_3 = asyncio.create_task(_lock_task_3(queue))

    await asyncio.sleep(5)

    assert queue.get() == 1
    assert queue.get() == 3
    assert queue.empty()

    task_1.cancel()
    task_2.cancel()
    task_3.cancel()
