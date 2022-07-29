import asyncio
import uuid
from multiprocessing import Queue, queues
from typing import Optional

import pytest

from etcetra import EtcdClient
from etcetra.types import LeaderKey


@pytest.mark.asyncio
async def test_election_service(etcd: EtcdClient, election_id: str):

    async def _campaign_task(value: str) -> LeaderKey:
        async with etcd.connect() as communicator:
            lease_id = await communicator.grant_lease(ttl=60 * 60)
            return await communicator.election_campaign(
                name=election_id,
                lease_id=lease_id,
                value=value,
            )

    async def _resign_task(leader: LeaderKey) -> None:
        async with etcd.connect() as communicator:
            await communicator.election_resign(leader)

    async def _leader_task() -> LeaderKey:
        async with etcd.connect() as communicator:
            return await communicator.election_leader(name=election_id)

    async def _proclaim_task(leader: LeaderKey, value: str) -> None:
        async with etcd.connect() as communicator:
            await communicator.election_proclaim(leader, value)

    async def _observe_task(election_id: str, queue: Optional[queues.Queue] = None) -> None:
        async with etcd.connect() as communicator:
            async for kv in communicator.election_observe(name=election_id):
                if queue:
                    queue.put(kv.value)

    # Campaign
    random_value = str(uuid.uuid4())
    leader_key = await _campaign_task(value=random_value)

    # Leader
    current_leader_key = await _leader_task()
    assert current_leader_key.lease == leader_key.lease

    election_event_queue: queues.Queue = Queue()
    observe_task = asyncio.create_task(_observe_task(election_id, queue=election_event_queue))
    await asyncio.sleep(3.0)

    # Proclaim
    next_random_value = str(uuid.uuid4())
    await _proclaim_task(leader=leader_key, value=next_random_value)

    # Observe
    initial_value = election_event_queue.get()
    assert initial_value == random_value
    proclaimed_value = election_event_queue.get()
    assert proclaimed_value == next_random_value

    observe_task.cancel()

    # Resign
    new_random_value = str(uuid.uuid4())
    new_campaign_task = _campaign_task(value=new_random_value)
    await _resign_task(leader=leader_key)
    new_leader_key = await asyncio.wait_for(new_campaign_task, timeout=None)
    current_leader_key = await _leader_task()
    assert current_leader_key.lease == new_leader_key.lease

    # Cleanup granted leases
    async with etcd.connect() as communicator:
        await communicator.revoke_lease(leader_key.lease)
        await communicator.revoke_lease(new_leader_key.lease)
