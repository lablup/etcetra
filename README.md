# etcetra

Pure python asyncio Etcd client.

## Installation

```bash
pip install etcetra
```

## API Documentation

Refer [here](/docs/references.md).

## Basic usage

All etcd operations managed by etcetra can be executed using `EtcdClient`.
`EtcdClient` instance is a wrapper which holds connection information to Etcd channel.
This instance is reusable, since actual connection to gRPC channel will be established
when you initiate connection calls (see below).

```python
from etcetra import EtcdClient, HostPortPair
etcd = EtcdClient(HostPortPair('127.0.0.1', 2379))
```

Like I mentioned above, actual connection establishment with Etcd's gRPC channel will be done
when you call `EtcdClient.connect()`. This call returns async context manager, which manages `EtcdCommunicator` instance.

```python
async with etcd.connect() as communicator:
    await communicator.put('testkey', 'testvalue')
    value = await communicator.get('testkey')
    print(value)  # testvalue
```

`EtcdCommunicator.get_prefix(prefix)` will return a dictionary containing all key-values with given key prefix.

```python
async with etcd.connect() as communicator:
    await communicator.put('/testdir', 'root')
    await communicator.put('/testdir/1', '1')
    await communicator.put('/testdir/2', '2')
    await communicator.put('/testdir/2/3', '3')
    test_dir = await communicator.get_prefix('/testdir')
    print(test_dir)  # {'/testdir': 'root', '/testdir/1': '1', '/testdir/2': '2', '/testdir/2/3': '3'}
```

## Operating with Etcd lock

Just like `EtcdClient.connect()`, you can easilly use etcd lock by calling `EtcdClient.with_lock(lock_name, timeout=None)`.

```python
async def first():
    async with etcd.with_lock('foolock') as communicator:
        value = await communicator.get('testkey')
        print('first:', value, end=' | ')

async def second():
    await asyncio.sleep(0.1)
    async with etcd.with_lock('foolock') as communicator:
        value = await communicator.get('testkey')
        print('second:', value)

async with etcd.connect() as communicator:
    await communicator.put('testkey', 'testvalue')
await asyncio.gather(first(), second())  # first: testvalue | second: testvalue
```

Adding `timeout` parameter to `EtcdClient.with_lock()` call will add a timeout to lock acquiring process.

```python
async def first():
    async with etcd.with_lock('foolock') as communicator:
        value = await communicator.get('testkey')
        print('first:', value)
        await asyncio.sleep(10)

async def second():
    await asyncio.sleep(0.1)
    async with etcd.with_lock('foolock', timeout=5) as communicator:
        value = await communicator.get('testkey')
        print('second:', value)

async with etcd.connect() as communicator:
    await communicator.put('testkey', 'testvalue')
await asyncio.gather(first(), second())  # asyncio.TimeoutError followed by first: testvalue output
```

## Watch

You can watch changes on key with `EtcdCommunicator.watch(key)`.

```python
async def watch():
    async with etcd.connect() as communicator:
        async for event in communicator.watch('testkey'):
            print(event.event, event.value)

async def update():
    await asyncio.sleep(0.1)
    async with etcd.connect() as communicator:
        await communicator.put('testkey', '1')
        await communicator.put('testkey', '2')
        await communicator.put('testkey', '3')
        await communicator.put('testkey', '4')
        await communicator.put('testkey', '5')

await asyncio.gather(watch(), update())
# WatchEventType.PUT 1
# WatchEventType.PUT 2
# WatchEventType.PUT 3
# WatchEventType.PUT 4
# WatchEventType.PUT 5
```

Watching changes on keys with specific prefix can be also done by `EtcdCommunicator.watch_prefix(key_prefix)`.

```python
async def watch():
    async with etcd.connect() as communicator:
        async for event in communicator.watch_prefix('/testdir'):
            print(event.event, event.key, event.value)

async def update():
    await asyncio.sleep(0.1)
    async with etcd.connect() as communicator:
        await communicator.put('/testdir', '1')
        await communicator.put('/testdir/foo', '2')
        await communicator.put('/testdir/bar', '3')
        await communicator.put('/testdir/foo/baz', '4')

await asyncio.gather(watch(), update())
# WatchEventType.PUT /testdir 1
# WatchEventType.PUT /testdir/foo 2
# WatchEventType.PUT /testdir/bar 3
# WatchEventType.PUT /testdir/foo/baz 4
```

## Transaction

You can run etcd transaction by calling `EtcdCommunicator.txn_compare(compares, txn_builder)`.

### Constructing compares

Constructing compare operations can be done by comparing `CompareKey` instance with value with Python's built-in comparison operators (`==`, `!=`, `>`, `<`).

```python
from etcetra import CompareKey
compares = [
    CompareKey('cmpkey1').value == 'foo',
    CompareKey('cmpkey2').value > 'bar',
]
```

### Executing transaction calls

```python
async with etcd.connect() with communicator:
    await communicator.put('cmpkey1', 'foo')
    await communicator.put('cmpkey2', 'baz')
    await communicator.put('successkey', 'asdf')

    def _txn(success, failure):
        success.get('successkey')

    values = await communicator.txn_compare(compares, _txn)
    print(values)  # ['asdf']
```

```python
compares = [
    CompareKey('cmpkey1').value == 'foo',
    CompareKey('cmpkey2').value < 'bar',
]
async with etcd.connect() with communicator:
    await communicator.put('failurekey', 'asdf')

    def _txn(success, failure):
        failure.get('failurekey')

    values = await communicator.txn_compare(compares, _txn)
    print(values)  # ['asdf']
```

If you don't need compare conditions for transaction, you can use `EtcdCommunicator.txn(txn_builder)`,
which is a shorthand for `EtcdCommunicator.txn_compare([], lambda success, failure: txn_builder(success))`.

```python
async with etcd.connect() with communicator:
    def _txn(action):
        action.get('cmpkey1')
        action.get('cmpkey2')

    values = await communicator.txn(_txn)
    print(values)  # ['foo', 'baz']
```

# Compiling Protobuf

```bash
$ scripts/compile_protobuf.py <target Etcd version>
```
