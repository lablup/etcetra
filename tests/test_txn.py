import pytest

from etcetra import EtcdClient, EtcdTransactionAction, CompareKey


@pytest.mark.asyncio
async def test_txn(etcd: EtcdClient):
    async with etcd.connect() as communicator:
        await communicator.put('/test/foo', 'bar')
        await communicator.put('/test/asd', '123')

        def _txn(action: EtcdTransactionAction):
            action.get('/test/asd')
            action.put('/test/qwe', 'rty')
            action.get('/test/foo')

        results = await communicator.txn(_txn)
        assert results[0] == {'/test/asd': '123'}
        assert results[1] is not None and results[1].get("revision") is not None
        assert results[2] == {'/test/foo': 'bar'}

        assert (await communicator.get('/test/qwe')) == 'rty'


@pytest.mark.asyncio
async def test_txn_compare_success(etcd: EtcdClient):
    async with etcd.connect() as communicator:
        await communicator.put('/test/cmpkey', 'asdf')

        def _txn(success: EtcdTransactionAction, failure: EtcdTransactionAction):
            success.put('/test/successkey', '123')
            failure.put('/test/failurekey', '456')

        await communicator.txn_compare([
            CompareKey('/test/cmpkey').value == 'asdf',
        ], _txn)

        assert (await communicator.get('/test/successkey')) == '123'
        assert (await communicator.get('/test/failurekey')) is None


@pytest.mark.asyncio
async def test_txn_compare_failure(etcd: EtcdClient):
    async with etcd.connect() as communicator:
        await communicator.put('/test/cmpkey', 'asdf')

        def _txn(success: EtcdTransactionAction, failure: EtcdTransactionAction):
            success.put('/test/successkey', '123')
            failure.put('/test/failurekey', '456')

        await communicator.txn_compare([
            CompareKey('/test/cmpkey').value == 'asdf1234',
        ], _txn)

        assert (await communicator.get('/test/successkey')) is None
        assert (await communicator.get('/test/failurekey')) == '456'
