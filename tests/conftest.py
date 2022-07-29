import os
import uuid

import pytest

from etcetra import EtcdClient, HostPortPair


@pytest.fixture
def etcd_addr():
    env_addr = os.environ.get('BACKEND_ETCD_ADDR')
    if env_addr is not None:
        return HostPortPair.parse(env_addr)
    return HostPortPair.parse('localhost:2379')


@pytest.fixture
async def etcd(etcd_addr):
    etcd = EtcdClient(etcd_addr)
    try:
        yield etcd
    finally:
        async with etcd.connect() as communicator:
            await communicator.delete_prefix('/test')
        del etcd


@pytest.fixture(scope="module")
def election_id() -> bytes:
    return f"test/{uuid.uuid4()}".encode("utf-8")
