import pytest

from etcetra import EtcdClient, HostPortPair
from etcetra.errors import EtcdUnknownError


@pytest.mark.asyncio
async def test_connect_error():
    etcd = EtcdClient(HostPortPair('127.0.0.1', 1))
    with pytest.raises(EtcdUnknownError):
        async with etcd.connect() as communicator:
            await communicator.get('/this/should/raise/error')
