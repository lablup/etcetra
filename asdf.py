import asyncio
from etcetra import EtcdClient, HostPortPair


async def main():
    etcd = EtcdClient(HostPortPair('127.0.0.1', 2379))

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


if __name__ == '__main__':
    asyncio.run(main())
