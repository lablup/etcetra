import asyncio
from queue import Queue
import time
import traceback
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


@pytest.mark.asyncio
async def test_lock_ttl(etcd: EtcdClient):
    queue: Queue[float] = Queue()

    async def _lock_task_1():
        try:
            conmgr = etcd.with_lock('/test/ttllocka', ttl=3)
            await conmgr.__aenter__()
            await asyncio.sleep(10)
        except Exception:
            traceback.print_exc()
            raise
        finally:
            conmgr._lock._keepalive_task.cancel()

    async def _lock_task_2(queue: Queue[float]):
        try:
            start = time.monotonic()
            async with etcd.with_lock('/test/ttllocka', ttl=60):
                queue.put(time.monotonic() - start)
        except Exception:
            traceback.print_exc()
            raise

    task_1 = asyncio.create_task(_lock_task_1())
    await asyncio.sleep(5)
    task_1.cancel()
    task_2 = asyncio.create_task(_lock_task_2(queue))
    await asyncio.sleep(5)

    assert not queue.empty()
    assert 2.5 < queue.get() < 3.5
    assert queue.empty()

    task_1.cancel()
    task_2.cancel()
