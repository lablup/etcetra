import pytest

from etcetra import EtcdClient


@pytest.mark.asyncio
async def test_put(etcd: EtcdClient):
    async with etcd.connect() as communicator:
        await communicator.put('/test/foo', 'bar')
        assert (await communicator.get('/test/foo')) == 'bar'

        await communicator.put('/test/foo', 'baz')
        assert (await communicator.get('/test/foo')) == 'baz'


@pytest.mark.asyncio
async def test_get(etcd: EtcdClient):
    async with etcd.connect() as communicator:
        await communicator.put('/test/foo', 'bar')
        await communicator.put('/test/foo/bar', 'asd')
        await communicator.put('/test/foo/baz', '1234')
        await communicator.put('/test/foo/baz/qwe', 'rty')

        assert (await communicator.get('/test/foo')) == 'bar'
        assert (await communicator.get('/test/somewhatnonexistingkey')) is None
        assert (await communicator.get_prefix('/test/foo/baz')) == {
            '/test/foo/baz': '1234',
            '/test/foo/baz/qwe': 'rty',
        }
        assert (await communicator.get_prefix('/test/foo/baz/')) == {
            '/test/foo/baz/qwe': 'rty',
        }

        assert (await communicator.keys_prefix('/test/foo')) == [
            '/test/foo', '/test/foo/bar', '/test/foo/baz', '/test/foo/baz/qwe',
        ]

        await communicator.delete('/test/foo/baz/qwe')

        assert (await communicator.keys_prefix('/test/foo')) == [
            '/test/foo', '/test/foo/bar', '/test/foo/baz',
        ]
