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
            async with etcd.with_lock('/test/ttllocka', ttl=3):
                await asyncio.sleep(5)
        except Exception:
            traceback.print_exc()
            raise

    async def _lock_task_2(queue: Queue[float]):
        try:
            start = time.monotonic()
            async with etcd.with_lock('/test/ttllocka', ttl=60):
                queue.put(time.monotonic() - start)
        except Exception:
            traceback.print_exc()
            raise

    task_1 = asyncio.create_task(_lock_task_1())
    await asyncio.sleep(1)
    task_2 = asyncio.create_task(_lock_task_2(queue))
    await asyncio.sleep(5)

    assert not queue.empty()
    assert 1.5 < queue.get() < 2.5
    assert queue.empty()

    task_1.cancel()
    task_2.cancel()


@pytest.mark.asyncio
async def test_lock_ttl_2(etcd: EtcdClient):
    queue: Queue[float] = Queue()

    async def _lock_task_1():
        async with etcd.with_lock('/test/ttl'):
            await asyncio.sleep(3)

    async def _lock_task_2():
        async with etcd.with_lock('/test/ttl', ttl=3):
            await asyncio.sleep(5)

    async def _lock_task_3(queue: Queue[float]):
        start = time.monotonic()
        async with etcd.with_lock('/test/ttl'):
            queue.put(time.monotonic() - start)

    task_1 = asyncio.create_task(_lock_task_1())
    await asyncio.sleep(1)
    task_2 = asyncio.create_task(_lock_task_2())
    await asyncio.sleep(4)
    task_3 = asyncio.create_task(_lock_task_3(queue))
    await asyncio.sleep(3)

    # Timeline
    # T+0: Task 1 starts and acquires the lock
    # T+1: Task 2 starts and tries to acquire the lock
    # T+3: Task 1 releases the lock and task 2 acquires the lock
    # T+5: Task 3 starts and tries to acquire the lock
    # T+6: Task 2 releases the lock and task 3 acquires the lock

    # The test is that TTL starts to count when the lock is acquired (T+3),
    # not when the task tries to acquire the lock (T+1). So 3 seconds TTL
    # expires at T+6, not T+4, blocking the task 3's attempt at T+5.

    assert not queue.empty()
    assert 0.5 < queue.get() < 1.5
    assert queue.empty()

    task_1.cancel()
    task_2.cancel()
    task_3.cancel()
