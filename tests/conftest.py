import os
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
