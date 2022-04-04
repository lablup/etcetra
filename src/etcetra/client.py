"""
Pure python asyncio Etcd client.
"""

from __future__ import annotations
import asyncio

from typing import (
    AsyncIterator,
    Callable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    OrderedDict,
    Protocol,
    TypeVar,
)
from async_timeout import timeout

import grpc
from grpc.aio import Channel

from .grpc_api import rpc_pb2, rpc_pb2_grpc
from .grpc_api import v3lock_pb2, v3lock_pb2_grpc
from .types import (
    DeleteRangeRequestType, EtcdCredential, EtcdLockOption, HostPortPair,
    PutRequestType, RangeRequestSortOrder, RangeRequestSortTarget, RangeRequestType,
    TransactionRequest, TxnReturnType, TxnReturnValues, WatchCreateRequestFilterType,
    WatchEvent, WatchEventType,
)
__all__ = (
    'EtcdClient',
    'EtcdCommunicator',
    'EtcdTransactionAction',
)
T = TypeVar('T', covariant=True)


class Proto(Protocol[T]):
    async def meth(self) -> T:
        pass


class EtcdClient:
    """
    Wrapper class of underlying actual Etcd API implementations (KV, Watch, Txn, ...).
    In most cases, user can perform most of the jobs by creating `EtcdClient` object.
    """
    addr: HostPortPair
    _creds: Optional[EtcdCredential]
    secure: bool
    encoding: str

    def __init__(
        self,
        addr: HostPortPair,
        credentials: Optional[EtcdCredential] = None,
        secure: bool = False,
        encoding: str = 'utf-8',
    ) -> None:
        """
        Creates `EtcdClient` instance.

        Parameters
        ---------
        addr
            Connection information of target Etcd cluster.
        credentials
            Authentication information of target Etcd cluster.
            When this value is `None`, `etcetra` will skip all Etcd authentication procedures.
        secure
            If this value is `True`, `etcetra` will try to communicate to Etcd cluster
            with secure gRPC channel.
        encoding
            Character encoding type to encode/decode all types of byte based strings.
            Defaults to `utf-8`.
        """
        self.addr = addr
        self._creds = credentials
        self.secure = secure
        self.encoding = encoding

    def _build_channel(self):
        if self.secure:
            chan = grpc.aio.secure_channel(str(self.addr))
        else:
            chan = grpc.aio.insecure_channel(str(self.addr))
        return chan

    def _build_connector_protocol(self) -> Proto[EtcdCommunicator]:
        chan = self._build_channel()
        _creds = self._creds

        class P(Proto):
            async def meth(self) -> EtcdCommunicator:
                communicator = EtcdCommunicator(chan)
                if creds := _creds:
                    await communicator._authenticate(creds.username, creds.password)
                return communicator
        return P()

    def connect(self):
        """
        Async context manager which establishes connection to Etcd cluster.

        Returns
        -------
        communicator: EtcdCommunicator
            An `EtcdCommunicator` instance.
        """
        return EtcdConnectionManager(self._build_connector_protocol())

    def with_lock(self, lock_name: str, timeout: Optional[float] = None):
        """
        Async context manager which establishes connection and then
        immediately tries to acquire lock with given lock name.
        Acquired lock will automatically released when user exits `with` context.

        Parameters
        ---------
        lock_name
            Name of Etcd lock to acquire.
        timeout
            Number of seconds to wait until lock is acquired. Defaults to `None`.
            If value is `None`, `with_lock` will wait forever until lock is acquired.

        Returns
        -------
        communicator: EtcdCommunicator
            An `EtcdCommunicator` instance.

        Raises
        -------
        asyncio.TimeoutError
            When timeout expires.
        """
        lock_opt = EtcdLockOption(lock_name, timeout=timeout)
        return EtcdConnectionManager(self._build_connector_protocol(), lock_option=lock_opt)


class EtcdConnectionManager:
    communicator_builder: Proto[EtcdCommunicator]

    _lock_option: Optional[EtcdLockOption]
    _lock_key: Optional[str]
    _communicator: Optional[EtcdCommunicator]

    def __init__(
        self,
        communicator_builder: Proto[EtcdCommunicator],
        lock_option: Optional[EtcdLockOption] = None,
    ) -> None:
        self.communicator_builder = communicator_builder
        self._lock_option = lock_option
        self._lock_key = None
        self._communicator = None

    async def __aenter__(self) -> EtcdCommunicator:
        if self._communicator is None:
            self._communicator = await self.communicator_builder.meth()
        if lock_opt := self._lock_option:
            self._lock_key = await self._communicator._lock(
                lock_opt.lock_name, timeout_seconds=lock_opt.timeout)
        return self._communicator

    async def __aexit__(self, exc_type, exc, tb):
        if self._communicator is None:
            raise ValueError('__aexit__ called before __aenter__ called')
        if self._lock_option is not None and self._lock_key is not None:
            await self._communicator._unlock(self._lock_key)
        await self._communicator.channel.close()
        if exc_type is not None:
            raise exc


class EtcdRequestGenerator:
    @classmethod
    def put(
        cls, key: str, value: Optional[str],
        lease: Optional[int] = None,
        ignore_value: bool = False,
        ignore_lease: bool = False,
        encoding='utf-8',
    ):
        # TODO: Implement prev_kv response
        return rpc_pb2.PutRequest(
            key=key.encode(encoding),
            value=value.encode(encoding) if value else None,
            lease=lease, ignore_lease=ignore_lease, ignore_value=ignore_value,
        )

    @classmethod
    def get(
        cls, key: str,
        limit: Optional[str] = None,
        max_create_revision: Optional[str] = None,
        max_mod_revision: Optional[str] = None,
        min_create_revision: Optional[str] = None,
        min_mod_revision: Optional[str] = None,
        revision: Optional[str] = None,
        serializable: bool = True,
        sort_order: RangeRequestSortOrder = RangeRequestSortOrder.NONE,
        sort_target: RangeRequestSortTarget = RangeRequestSortTarget.KEY,
        encoding='utf-8',
    ):
        return rpc_pb2.RangeRequest(
            key=key.encode(encoding),
            limit=limit,
            max_create_revision=max_create_revision,
            max_mod_revision=max_mod_revision,
            min_create_revision=min_create_revision,
            min_mod_revision=min_mod_revision,
            revision=revision,
            serializable=serializable,
            sort_order=sort_order.value,
            sort_target=sort_target.value,
        )

    @classmethod
    def get_range(
        cls, key: str, range_end: str,
        limit: Optional[str] = None,
        max_create_revision: Optional[str] = None,
        max_mod_revision: Optional[str] = None,
        min_create_revision: Optional[str] = None,
        min_mod_revision: Optional[str] = None,
        revision: Optional[str] = None,
        serializable: bool = True,
        sort_order: RangeRequestSortOrder = RangeRequestSortOrder.NONE,
        sort_target: RangeRequestSortTarget = RangeRequestSortTarget.KEY,
        encoding='utf-8',
    ):
        return rpc_pb2.RangeRequest(
            key=key.encode(encoding),
            range_end=range_end.encode(encoding),
            limit=limit,
            max_create_revision=max_create_revision,
            max_mod_revision=max_mod_revision,
            min_create_revision=min_create_revision,
            min_mod_revision=min_mod_revision,
            revision=revision,
            serializable=serializable,
            sort_order=sort_order.value,
            sort_target=sort_target.value,
        )

    @classmethod
    def get_prefix(
        cls, key: str,
        limit: Optional[str] = None,
        max_create_revision: Optional[str] = None,
        max_mod_revision: Optional[str] = None,
        min_create_revision: Optional[str] = None,
        min_mod_revision: Optional[str] = None,
        revision: Optional[str] = None,
        serializable: bool = True,
        sort_order: RangeRequestSortOrder = RangeRequestSortOrder.NONE,
        sort_target: RangeRequestSortTarget = RangeRequestSortTarget.KEY,
        encoding='utf-8',
    ):
        encoded_key = key.encode(encoding)
        if key[-1] == '/' and len(key) >= 2:
            range_end = encoded_key[:-2] + bytes([encoded_key[-2] + 1]) + b'/'
        else:
            range_end = encoded_key[:-1] + bytes([encoded_key[-1] + 1])
        return rpc_pb2.RangeRequest(
            key=encoded_key,
            range_end=range_end,
            limit=limit,
            max_create_revision=max_create_revision,
            max_mod_revision=max_mod_revision,
            min_create_revision=min_create_revision,
            min_mod_revision=min_mod_revision,
            revision=revision,
            serializable=serializable,
            sort_order=sort_order.value,
            sort_target=sort_target.value,
        )

    @classmethod
    def delete(
        cls, key: str,
        encoding='utf-8',
    ):
        # TODO: Implement prev_kv response
        return rpc_pb2.DeleteRangeRequest(
            key=key.encode(encoding),
        )

    @classmethod
    def delete_range(
        cls, key: str, range_end: str,
        encoding='utf-8',
    ):
        # TODO: Implement prev_kv response
        return rpc_pb2.DeleteRangeRequest(
            key=key.encode(encoding),
            range_end=range_end.encode(encoding),
        )

    @classmethod
    def delete_prefix(
        cls, key: str,
        encoding='utf-8',
    ):
        # TODO: Implement prev_kv response
        encoded_key = key.encode(encoding)
        if key[-1] == '/' and len(key) >= 2:
            range_end = encoded_key[:-2] + bytes([encoded_key[-2] + 1]) + b'/'
        else:
            range_end = encoded_key[:-1] + bytes([encoded_key[-1] + 1])
        return rpc_pb2.DeleteRangeRequest(
            key=encoded_key,
            range_end=range_end,
        )

    @classmethod
    def keys_range(
        cls, key: str, range_end: str,
        limit: Optional[str] = None,
        max_create_revision: Optional[str] = None,
        max_mod_revision: Optional[str] = None,
        min_create_revision: Optional[str] = None,
        min_mod_revision: Optional[str] = None,
        revision: Optional[str] = None,
        serializable: bool = True,
        sort_order: RangeRequestSortOrder = RangeRequestSortOrder.NONE,
        sort_target: RangeRequestSortTarget = RangeRequestSortTarget.KEY,
        encoding='utf-8',
    ):
        return rpc_pb2.RangeRequest(
            key=key.encode(encoding),
            range_end=range_end.encode(encoding),
            keys_only=True,
            limit=limit,
            max_create_revision=max_create_revision,
            max_mod_revision=max_mod_revision,
            min_create_revision=min_create_revision,
            min_mod_revision=min_mod_revision,
            revision=revision,
            serializable=serializable,
            sort_order=sort_order.value,
            sort_target=sort_target.value,
        )

    @classmethod
    def keys_prefix(
        cls, key: str,
        limit: Optional[str] = None,
        max_create_revision: Optional[str] = None,
        max_mod_revision: Optional[str] = None,
        min_create_revision: Optional[str] = None,
        min_mod_revision: Optional[str] = None,
        revision: Optional[str] = None,
        serializable: bool = True,
        sort_order: RangeRequestSortOrder = RangeRequestSortOrder.NONE,
        sort_target: RangeRequestSortTarget = RangeRequestSortTarget.KEY,
        encoding='utf-8',
    ):
        encoded_key = key.encode(encoding)
        if key[-1] == '/' and len(key) >= 2:
            range_end = encoded_key[:-2] + bytes([encoded_key[-2] + 1]) + b'/'
        else:
            range_end = encoded_key[:-1] + bytes([encoded_key[-1] + 1])
        return rpc_pb2.RangeRequest(
            key=encoded_key,
            range_end=range_end,
            keys_only=True,
            limit=limit,
            max_create_revision=max_create_revision,
            max_mod_revision=max_mod_revision,
            min_create_revision=min_create_revision,
            min_mod_revision=min_mod_revision,
            revision=revision,
            serializable=serializable,
            sort_order=sort_order.value,
            sort_target=sort_target.value,
        )


class EtcdCommunicator:
    """
    Performs actual API calls to Etcd cluster and returns result.
    """
    encoding: str
    channel: Channel

    def __init__(self, channel: Channel, encoding: str = 'utf-8'):
        """
        Creates `EtcdCommunicator` instance.
        In most cases, users won't have to directly create `EtcdCommunicator` class;
        It can be automatically done by `EtcdClient.connect()` or `EtcdClient.with_lock()`.

        Parameters
        ---------
        channel
            Async gRPC Channel to interact.

        encoding
            Character encoding type to encode/decode all types of byte based strings.
            Defaults to `utf-8`.
        """
        self.encoding = encoding
        self.channel = channel

    async def _authenticate(self, username: str, password: str):
        """
        Tries to authenticate to Etcd server with given credentials.
        In most cases, `EtcdClient` will automatically handle authentication process.
        """
        stub = rpc_pb2_grpc.AuthStub(self.channel)
        return await stub.Authenticate(
            rpc_pb2.AuthenticateRequest(name=username, password=password),
        )

    async def put(
        self, key: str, value: Optional[str],
        lease: Optional[int] = None,
        prev_kv: bool = False,
        encoding: Optional[str] = None,
    ) -> Optional[str]:
        """
        Puts given key into the key-value store.

        Parameters
        ---------
        key
            The key to put into the key-value store
        value
            The value to associate with the key in the key-value store.
        lease
            The lease ID to associate with the key in the key-value store. Defaults to `None`.
            `None` lease indicates no lease.
        prev_kv
            If this value is `True`, gets the previous value before changing it and returns it.
            Defaults to `False`.
        encoding
            Character encoding type to encode/decode all types of byte based strings.
            If this value is `None`, this method will use default encoding which is set when creating
            this instance.
            Defaults to `utf-8`.

        Returns
        -------
        value: Optional[str]
            If `prev_kv` is set to `True` and previous value exists, returns previous value.
            Otherwise it will just return `None`.
        """
        if encoding is None:
            encoding = self.encoding
        ignore_value = value is None
        if ignore_value:
            value = ''
        stub = rpc_pb2_grpc.KVStub(self.channel)
        response = await stub.Put(
            EtcdRequestGenerator.put(
                key, value,
                lease=lease, ignore_value=ignore_value,
                encoding=encoding,
            ),
        )
        if prev_kv and response.prev_kv is not None and response.prev_kv.value is not None:
            return response.prev_kv.value.decode(encoding)
        return None

    async def get(
        self, key: str,
        max_create_revision: Optional[str] = None,
        max_mod_revision: Optional[str] = None,
        min_create_revision: Optional[str] = None,
        min_mod_revision: Optional[str] = None,
        revision: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> Optional[str]:
        """
        Gets value associated with given key from the key-value store.

        Parameters
        ---------
        key
            The key to look up.
        max_create_revision
            The upper bound for returned key create revisions;
            all keys with greater create revisions will be filtered away.
        max_mod_revision
            The upper bound for returned key mod revisions;
            all keys with greater mod revisions will be filtered away.
        min_create_revision
            The lower bound for returned key create revisions;
            all keys with lesser create revisions will be filtered away.
        min_mod_revision
            The lower bound for returned key mod revisions;
            all keys with lesser mod revisions will be filtered away.
        revision
            The point-in-time of the key-value store to use for the range.
            If revision is less or equal to zero, the range is over the newest key-value store.
            If the revision has been compacted, ErrCompacted is returned as a response.
        encoding
            Character encoding type to encode/decode all types of byte based strings.
            If this value is `None`, this method will use default encoding which is set when creating
            this instance.
            Defaults to `utf-8`.

        Returns
        -------
        value: Optional[str]
            Returns value if given key exists. Otherwise it will return `None`.
        """
        if encoding is None:
            encoding = self.encoding
        stub = rpc_pb2_grpc.KVStub(self.channel)
        response = await stub.Range(
            EtcdRequestGenerator.get(
                key,
                max_create_revision=max_create_revision,
                max_mod_revision=max_mod_revision,
                min_create_revision=min_create_revision,
                min_mod_revision=min_mod_revision,
                revision=revision,
                serializable=True,
                sort_order=RangeRequestSortOrder.NONE,
                sort_target=RangeRequestSortTarget.KEY,
                encoding=encoding,
            ),
        )
        if len(response.kvs) > 0:
            return response.kvs[0].value.decode(encoding)
        else:
            return None

    async def get_prefix(
        self, key: str,
        max_create_revision: Optional[str] = None,
        max_mod_revision: Optional[str] = None,
        min_create_revision: Optional[str] = None,
        min_mod_revision: Optional[str] = None,
        revision: Optional[str] = None,
        sort_order: RangeRequestSortOrder = RangeRequestSortOrder.NONE,
        sort_target: RangeRequestSortTarget = RangeRequestSortTarget.KEY,
        encoding: Optional[str] = None,
    ) -> Mapping[str, str]:
        """
        Gets the key-value in dictionary from the key-value store with given key prefix.
        i.e. `get_prefix('/sorna/local')` call looks up all keys which has `/sorna/local` prefix.

        Parameters
        ---------
        key
            The key prefix to look up.
        max_create_revision
            The upper bound for returned key create revisions;
            all keys with greater create revisions will be filtered away.
        max_mod_revision
            The upper bound for returned key mod revisions;
            all keys with greater mod revisions will be filtered away.
        min_create_revision
            The lower bound for returned key create revisions;
            all keys with lesser create revisions will be filtered away.
        min_mod_revision
            The lower bound for returned key mod revisions;
            all keys with lesser mod revisions will be filtered away.
        revision
            The point-in-time of the key-value store to use for the range.
            If revision is less or equal to zero, the range is over the newest key-value store.
            If the revision has been compacted, ErrCompacted is returned as a response.
        sort_order
            Sort order. Defaults to `RangeRequestSortOrder.NONE`.
        sort_target
            Sort target. Defaults to `RangeRequestSortTarget.KEY`.
        encoding
            Character encoding type to encode/decode all types of byte based strings.
            If this value is `None`, this method will use default encoding which is set when creating
            this instance.
            Defaults to `utf-8`.

        Returns
        -------
        value: Mapping[str, str]
            Returns dictionary with all key-values which matches given key prefix.
        """
        if encoding is None:
            encoding = self.encoding
        stub = rpc_pb2_grpc.KVStub(self.channel)
        response = await stub.Range(
            EtcdRequestGenerator.get_prefix(
                key,
                max_create_revision=max_create_revision,
                max_mod_revision=max_mod_revision,
                min_create_revision=min_create_revision,
                min_mod_revision=min_mod_revision,
                revision=revision,
                serializable=True,
                sort_order=sort_order,
                sort_target=sort_target,
                encoding=encoding,
            ),
        )
        ret: MutableMapping[str, str] = OrderedDict()
        for x in response.kvs:
            ret[x.key.decode(encoding)] = x.value.decode(encoding)
        return ret

    async def get_range(
        self, key: str, range_end: str,
        limit: Optional[str] = None,
        max_create_revision: Optional[str] = None,
        max_mod_revision: Optional[str] = None,
        min_create_revision: Optional[str] = None,
        min_mod_revision: Optional[str] = None,
        revision: Optional[str] = None,
        sort_order: RangeRequestSortOrder = RangeRequestSortOrder.NONE,
        sort_target: RangeRequestSortTarget = RangeRequestSortTarget.KEY,
        encoding: Optional[str] = None,
    ) -> Mapping[str, str]:
        """
        Gets the key-value in dictionary from the key-value store with keys in [key, range_end) range.

        Parameters
        ---------
        key
            Start of key range.
        range_end
            End of key range.
        max_create_revision
            The upper bound for returned key create revisions;
            all keys with greater create revisions will be filtered away.
        max_mod_revision
            The upper bound for returned key mod revisions;
            all keys with greater mod revisions will be filtered away.
        min_create_revision
            The lower bound for returned key create revisions;
            all keys with lesser create revisions will be filtered away.
        min_mod_revision
            The lower bound for returned key mod revisions;
            all keys with lesser mod revisions will be filtered away.
        revision
            The point-in-time of the key-value store to use for the range.
            If revision is less or equal to zero, the range is over the newest key-value store.
            If the revision has been compacted, ErrCompacted is returned as a response.
        sort_order
            Sort order. Defaults to `RangeRequestSortOrder.NONE`.
        sort_target
            Sort target. Defaults to `RangeRequestSortTarget.KEY`.
        encoding
            Character encoding type to encode/decode all types of byte based strings.
            If this value is `None`, this method will use default encoding which is set when creating
            this instance.
            Defaults to `utf-8`.

        Returns
        -------
        value: Mapping[str, str]
            Returns dictionary with all key-values which matches given key prefix.
        """
        if encoding is None:
            encoding = self.encoding
        stub = rpc_pb2_grpc.KVStub(self.channel)
        response = await stub.Range(
            EtcdRequestGenerator.get_range(
                key, range_end,
                limit=limit,
                max_create_revision=max_create_revision,
                max_mod_revision=max_mod_revision,
                min_create_revision=min_create_revision,
                min_mod_revision=min_mod_revision,
                revision=revision,
                serializable=True,
                sort_order=sort_order,
                sort_target=sort_target,
                encoding=encoding,
            ),
        )
        ret: MutableMapping[str, str] = OrderedDict()
        for x in response.kvs:
            ret[x.key.decode(encoding)] = x.value.decode(encoding)
        return ret

    async def delete(
        self, key: str,
        prev_kv: bool = False, encoding: Optional[str] = None,
    ) -> Optional[str]:
        """
        Deletes the given key the key-value store.
        A delete request increments the revision of the key-value store
        and generates a delete event in the event history for every deleted key.

        Parameters
        ---------
        key
            The key to delete.
        prev_kv
            If this value set to `True` and previous value with associated target key exists,
            this method will return previous value.
        encoding
            Character encoding type to encode/decode all types of byte based strings.
            If this value is `None`, this method will use default encoding which is set when creating
            this instance.
            Defaults to `utf-8`.

        Returns
        ------
        value: Optional[str]
            If `prev_kv` is set to `True` and previous value exists, returns previous value.
            Otherwise it will just return `None`.
        """
        if encoding is None:
            encoding = self.encoding
        stub = rpc_pb2_grpc.KVStub(self.channel)
        response = await stub.DeleteRange(EtcdRequestGenerator.delete(key, encoding=encoding))
        if prev_kv and len(response.prev_kvs) > 0:
            return response.prev_kvs[0].value.decode(encoding)
        else:
            return None

    async def delete_prefix(
        self, key: str,
        prev_kv: bool = False, encoding: Optional[str] = None,
    ) -> Optional[List[Optional[str]]]:
        """
        Deletes keys with given prefix and its associated values from the key-value store.
        A delete request increments the revision of the key-value store
        and generates a delete event in the event history for every deleted key.

        Parameters
        ---------
        key
            The key prefix to delete.
        prev_kv
            If this value set to `True` and previous value with associated target key exists,
            this method will return previous value.
        encoding
            Character encoding type to encode/decode all types of byte based strings.
            If this value is `None`, this method will use default encoding which is set when creating
            this instance.
            Defaults to `utf-8`.

        Returns
        ------
        values: Optional[List[Optional[str]]]
            If `prev_kv` is set to `True` and previous value exists, returns previous value.
            Otherwise it will just return `None`.
        """
        if encoding is None:
            encoding = self.encoding
        stub = rpc_pb2_grpc.KVStub(self.channel)
        response = await stub.DeleteRange(EtcdRequestGenerator.delete_prefix(key, encoding=encoding))
        if prev_kv:
            return [
                x.value.decode(encoding) if x.value is not None else None
                for x in response.prev_kvs
            ]
        else:
            return None

    async def delete_range(
        self, key: str, range_end: str,
        prev_kv: bool = False, encoding: Optional[str] = None,
    ) -> Optional[List[Optional[str]]]:
        """
        Deletes the given range from the key-value store.
        A delete request increments the revision of the key-value store
        and generates a delete event in the event history for every deleted key.

        Parameters
        ---------
        key
            Start of key range.
        range_end
            End of key range.
        prev_kv
            If this value set to `True` and previous value with associated target key exists,
            this method will return previous value.
        encoding
            Character encoding type to encode/decode all types of byte based strings.
            If this value is `None`, this method will use default encoding which is set when creating
            this instance.
            Defaults to `utf-8`.

        Returns
        ------
        values: Optional[str]
            If `prev_kv` is set to `True` and previous value exists, returns previous value.
            Otherwise it will just return `None`.
        """
        if encoding is None:
            encoding = self.encoding
        stub = rpc_pb2_grpc.KVStub(self.channel)
        response = await stub.DeleteRange(
            EtcdRequestGenerator.delete_range(key, range_end, encoding=encoding))
        if prev_kv:
            return [
                x.value.decode(encoding) if x.value is not None else None
                for x in response.prev_kvs
            ]
        else:
            return None

    async def keys_prefix(
        self, key: str,
        max_create_revision: Optional[str] = None,
        max_mod_revision: Optional[str] = None,
        min_create_revision: Optional[str] = None,
        min_mod_revision: Optional[str] = None,
        revision: Optional[str] = None,
        sort_order: RangeRequestSortOrder = RangeRequestSortOrder.NONE,
        sort_target: RangeRequestSortTarget = RangeRequestSortTarget.KEY,
        encoding: Optional[str] = None,
    ) -> List[str]:
        """
        Gets the keys which has given prefix from the key-value store.

        Parameters
        ---------
        key
            The key prefix to look up.
        max_create_revision
            The upper bound for returned key create revisions;
            all keys with greater create revisions will be filtered away.
        max_mod_revision
            The upper bound for returned key mod revisions;
            all keys with greater mod revisions will be filtered away.
        min_create_revision
            The lower bound for returned key create revisions;
            all keys with lesser create revisions will be filtered away.
        min_mod_revision
            The lower bound for returned key mod revisions;
            all keys with lesser mod revisions will be filtered away.
        revision
            The point-in-time of the key-value store to use for the range.
            If revision is less or equal to zero, the range is over the newest key-value store.
            If the revision has been compacted, ErrCompacted is returned as a response.
        sort_order
            Sort order. Defaults to `RangeRequestSortOrder.NONE`.
        sort_target
            Sort target. Defaults to `RangeRequestSortTarget.KEY`.
        encoding
            Character encoding type to encode/decode all types of byte based strings.
            If this value is `None`, this method will use default encoding which is set when creating
            this instance.
            Defaults to `utf-8`.

        Returns
        -------
        keys: List[str]
            Returns list of found keys.
        """
        if encoding is None:
            encoding = self.encoding
        stub = rpc_pb2_grpc.KVStub(self.channel)
        response = await stub.Range(
            EtcdRequestGenerator.keys_prefix(
                key,
                max_create_revision=max_create_revision,
                max_mod_revision=max_mod_revision,
                min_create_revision=min_create_revision,
                min_mod_revision=min_mod_revision,
                revision=revision,
                serializable=True,
                sort_order=sort_order,
                sort_target=sort_target,
                encoding=encoding,
            ),
        )
        return [x.key.decode(encoding) for x in response.kvs]

    async def keys_range(
        self, key: str, range_end: str,
        limit: Optional[str] = None,
        max_create_revision: Optional[str] = None,
        max_mod_revision: Optional[str] = None,
        min_create_revision: Optional[str] = None,
        min_mod_revision: Optional[str] = None,
        revision: Optional[str] = None,
        serializable: bool = True,
        sort_order: RangeRequestSortOrder = RangeRequestSortOrder.NONE,
        sort_target: RangeRequestSortTarget = RangeRequestSortTarget.KEY,
        encoding: Optional[str] = None,
    ) -> List[str]:
        """
        Gets the keys in the range from the key-value store.

        Parameters
        ---------
        key
            Start of key range.
        range_end
            End of key range.
        max_create_revision
            The upper bound for returned key create revisions;
            all keys with greater create revisions will be filtered away.
        max_mod_revision
            The upper bound for returned key mod revisions;
            all keys with greater mod revisions will be filtered away.
        min_create_revision
            The lower bound for returned key create revisions;
            all keys with lesser create revisions will be filtered away.
        min_mod_revision
            The lower bound for returned key mod revisions;
            all keys with lesser mod revisions will be filtered away.
        revision
            The point-in-time of the key-value store to use for the range.
            If revision is less or equal to zero, the range is over the newest key-value store.
            If the revision has been compacted, ErrCompacted is returned as a response.
        sort_order
            Sort order. Defaults to `RangeRequestSortOrder.NONE`.
        sort_target
            Sort target. Defaults to `RangeRequestSortTarget.KEY`.
        encoding
            Character encoding type to encode/decode all types of byte based strings.
            If this value is `None`, this method will use default encoding which is set when creating
            this instance.
            Defaults to `utf-8`.

        Returns
        -------
        keys: List[str]
            Returns list of found keys.
        """
        if encoding is None:
            encoding = self.encoding
        stub = rpc_pb2_grpc.KVStub(self.channel)
        response = await stub.Range(
            EtcdRequestGenerator.keys_range(
                key, range_end,
                limit=limit,
                max_create_revision=max_create_revision,
                max_mod_revision=max_mod_revision,
                min_create_revision=min_create_revision,
                min_mod_revision=min_mod_revision,
                revision=revision,
                serializable=serializable,
                sort_order=sort_order,
                sort_target=sort_target,
                encoding=encoding,
            ),
        )
        return [x.key.decode(encoding) for x in response.kvs]

    async def _lock(
        self, name: str,
        lease: Optional[int] = None, encoding: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> str:
        """
        Acquires a distributed shared lock on a given named lock.
        On success, it will return a unique key that exists so long as the lock is held by the caller.
        This key can be used in conjunction with transactions to safely ensure updates to etcd
        only occur while holding lock ownership.
        The lock is held until Unlock is called on the key or the lease associate with the owner expires.
        In normal cases `EtcdClient.with_lock()` will automatically handle lock/unlock process.
        """
        if encoding is None:
            encoding = self.encoding
        stub = v3lock_pb2_grpc.LockStub(self.channel)
        async with timeout(timeout_seconds):
            response = await stub.Lock(
                v3lock_pb2.LockRequest(
                    name=name.encode(encoding),
                    lease=str(lease) if lease is not None else None,
                ),
            )
            return response.key.decode(encoding)

    async def _unlock(self, key: str, encoding: Optional[str] = None):
        """
        Takes a key returned by Lock and releases the hold on lock.
        The next Lock caller waiting for the lock will then be woken up and given ownership of the lock.
        In normal cases `EtcdClient.with_lock()` will automatically handle lock/unlock process.
        """
        if encoding is None:
            encoding = self.encoding
        stub = v3lock_pb2_grpc.LockStub(self.channel)
        await stub.Unlock(
            v3lock_pb2.UnlockRequest(
                key=key.encode(encoding),
            ),
        )

    async def _watch_impl(
        self, key: bytes, encoding: str,
        ready_event: Optional[asyncio.Event] = None,
        filters: Optional[List[WatchCreateRequestFilterType]] = None,
        fragment: bool = False,
        prev_kv: bool = False,
        progress_notify: bool = True,
        range_end: Optional[bytes] = None,
        start_revision: Optional[int] = None,
        watch_id: Optional[int] = None,
    ) -> AsyncIterator[WatchEvent]:
        """
        Actual implementation of `watch` procedure.
        """
        stub = rpc_pb2_grpc.WatchStub(self.channel)

        request = rpc_pb2.WatchRequest()
        request.create_request.key = key
        request.create_request.fragment = fragment
        for e in (filters or []):
            request.create_request.filters.extend([e.value])
        request.create_request.prev_kv = prev_kv
        request.create_request.progress_notify = progress_notify
        if range_end is not None:
            request.create_request.range_end = range_end
        if start_revision is not None:
            request.create_request.start_revision = str(start_revision)
        if watch_id is not None:
            request.create_request.watch_id = str(watch_id)

        stream = stub.Watch()
        await stream.write(request)

        try:
            if ready_event is not None:
                ready_event.set()
            while True:
                response = await stream.read()
                watch_id = response.watch_id
                for event in response.events:
                    if event.type == 0:
                        event_type = WatchEventType.PUT
                    if event.type == 1:
                        event_type = WatchEventType.DELETE
                    if prev_kv and event.prev_kv is not None and event.prev_kv.value is not None:
                        prev_value = event.prev_kv.value.decode(encoding)
                    else:
                        prev_value = None
                    yield WatchEvent(
                        event.kv.key.decode(encoding),
                        event.kv.value.decode(encoding) if event.kv.value is not None else None,
                        prev_value,
                        event_type,
                    )
        finally:
            if watch_id is not None and not stream.done():
                request = rpc_pb2.WatchRequest()
                request.cancel_request.watch_id = watch_id
                await stream.write(request)

    def watch(
        self, key: str,
        ready_event: Optional[asyncio.Event] = None,
        filters: Optional[List[WatchCreateRequestFilterType]] = None,
        prev_kv: bool = False,
        progress_notify: bool = False,
        start_revision: Optional[int] = None,
        watch_id: Optional[int] = None,
        encoding: Optional[str] = None,
    ) -> AsyncIterator[WatchEvent]:
        """
        Async iterator which watches for events happening or that have happened.
        Both input and output are streams; the input stream is for creating and canceling watchers
        and the output stream sends events.
        One watch RPC can watch on multiple key ranges, streaming events for several watches at once.
        The entire event history can be watched starting from the last compaction revision.

        Parameters
        ---------
        key
            The key to watch events.
        ready_event
            If this value is set, `Event.set()` will be called
            when watch is ready to accept events.
        filters
            Events to filter. Defaults to `None`.
            If this list is `None`, `watch` will yield all types of event.
        prev_kv
            If this value is set to `True`, event will be yielded with previous value supplied.
        progress_notify
            progress_notify is set so that the etcd server will periodically send a WatchResponse
            with no events to the new watcher if there are no recent events.
            It is useful when clients wish to recover a disconnected watcher
            starting from a recent known revision.
            The etcd server may decide how often it will send notifications based on current load.
        start_revision
            An optional revision to watch from (inclusive). No start_revision is "now".
        watch_id
            If watch_id is provided and non-zero, it will be assigned to this watcher.
            Since creating a watcher in etcd is not a synchronous operation,
            this can be used ensure that ordering is correct
            when creating multiple watchers on the same stream.
            Creating a watcher with an ID already in use on the stream
            will cause an error to be returned.
        encoding
            Character encoding type to encode/decode all types of byte based strings.
            If this value is `None`, this method will use default encoding which is set when creating
            this instance.
            Defaults to `utf-8`.

        Returns
        -------
        event: AsyncIterator[WatchEvent]
            A `WatchEvent` object containing event information.
        """
        if encoding is None:
            encoding = self.encoding

        return self._watch_impl(
            key.encode(encoding), encoding,
            ready_event=ready_event, filters=filters, prev_kv=prev_kv,
            progress_notify=progress_notify, start_revision=start_revision,
            watch_id=watch_id,
        )

    def watch_prefix(
        self, key: str,
        ready_event: Optional[asyncio.Event] = None,
        filters: Optional[List[WatchCreateRequestFilterType]] = None,
        prev_kv: bool = False,
        progress_notify: bool = True,
        start_revision: Optional[int] = None,
        watch_id: Optional[int] = None,
        encoding: Optional[str] = None,
    ) -> AsyncIterator[WatchEvent]:
        """
        Watches for events happening or that have happened along keys with given prefix.
        Both input and output are streams; the input stream is for creating and canceling watchers
        and the output stream sends events.
        One watch RPC can watch on multiple key ranges, streaming events for several watches at once.
        The entire event history can be watched starting from the last compaction revision.

        Parameters
        ---------
        key
            The key prefix to watch events.
        ready_event
            If this value is set, `Event.set()` will be called
            when watch is ready to accept events.
        filters
            Events to filter. Defaults to `None`.
            If this list is `None`, `watch` will yield all types of event.
        prev_kv
            If this value is set to `True`, event will be yielded with previous value supplied.
        progress_notify
            progress_notify is set so that the etcd server will periodically send a WatchResponse
            with no events to the new watcher if there are no recent events.
            It is useful when clients wish to recover a disconnected watcher
            starting from a recent known revision.
            The etcd server may decide how often it will send notifications based on current load.
        start_revision
            An optional revision to watch from (inclusive). No start_revision is "now".
        watch_id
            If watch_id is provided and non-zero, it will be assigned to this watcher.
            Since creating a watcher in etcd is not a synchronous operation,
            this can be used ensure that ordering is correct
            when creating multiple watchers on the same stream.
            Creating a watcher with an ID already in use on the stream
            will cause an error to be returned.
        encoding
            Character encoding type to encode/decode all types of byte based strings.
            If this value is `None`, this method will use default encoding which is set when creating
            this instance.
            Defaults to `utf-8`.

        Returns
        -------
        event: AsyncIterator[WatchEvent]
            A `WatchEvent` object containing event information.
        """
        if encoding is None:
            encoding = self.encoding

        encoded_key = key.encode(encoding)
        if key[-1] == '/' and len(key) >= 2:
            range_end = encoded_key[:-2] + bytes([encoded_key[-2] + 1]) + b'/'
        else:
            range_end = encoded_key[:-1] + bytes([encoded_key[-1] + 1])
        return self._watch_impl(
            key.encode(encoding), encoding,
            ready_event=ready_event, filters=filters, prev_kv=prev_kv,
            range_end=range_end, progress_notify=progress_notify,
            start_revision=start_revision, watch_id=watch_id,
        )

    async def txn(
        self,
        txn_builder: Callable[[EtcdTransactionAction], None],
        encoding: Optional[str] = None,
    ) -> TxnReturnValues:
        """
        A shorthand helper for `Txn`, with no `compare` arguments.
        This can be helpful when user just wants to execute transaction without
        any conditions.

        .. code-block:: python

            >>> await communicator.put('/tmp/successkey', '1111')
            >>> def _txn_builder(action):
            ...     action.get('/tmp/successkey')
            ...
            >>> values = await communicator.txn(_txn_builder)
            >>> print(values)  # ['1111']

        Parameters
        ---------
        txn_builder
            Function which accepts `EtcdTransactionAction` as argument and performs
            all KV calls.
        encoding
            Character encoding type to encode/decode all types of byte based strings.
            If this value is `None`, this method will use default encoding which is set when creating
            this instance.
            Defaults to `utf-8`.

        Returns
        -------
        values: List[TxnReturnType]
            Values returned in each calls inside transaction.
            If the call is `put` or `delete`, `None` will take that place.
        """
        results, _ = await self.txn_compare(
            [],
            lambda success, _: txn_builder(success),
            encoding=encoding,
        )
        return results

    async def txn_compare(
        self,
        compares: List[rpc_pb2.Compare],  # type: ignore
        txn_builder: Callable[[EtcdTransactionAction, EtcdTransactionAction], None],
        encoding: Optional[str] = None,
    ) -> TxnReturnType:
        """
        Processes multiple requests in a single transaction.
        A txn request increments the revision of the key-value store
        and generates events with the same revision for every completed request.
        It is not allowed to modify the same key several times within one txn.

        .. code-block:: python

            >>> from etcetra import CompareKey
            >>> await communicator.put('/tmp/successkey', '1111')
            >>> await communicator.put('/tmp/comparekey', 'asd')
            >>> await communicator.put('/tmp/comparekey2', 'asdg')
            >>> def _txn_builder(success, failure):
            ...     success.get('/tmp/successkey')
            ...
            >>> values = await communicator.txn_compare(
                    [
                        CompareKey('/tmp/comparekey').value == 'asd'],
                        CompareKey('/tmp/comparekey2').value > 'asdf'
                    ],
                    _txn_builder,
                )
            >>> print(values)  # ['1111']

        Parameters
        ---------
        compare
            List of predicates representing a conjunction of terms.
            If the comparisons succeed, then the success requests will be processed in order,
            and the response will contain their respective responses in order.
            If the comparisons fail, then the failure requests will be processed in order,
            and the response will contain their respective responses in order.
        txn_builder
            Function which accepts `EtcdTransactionAction` as argument and performs
            all KV calls.
        encoding
            Character encoding type to encode/decode all types of byte based strings.
            If this value is `None`, this method will use default encoding which is set when creating
            this instance.
            Defaults to `utf-8`.

        Returns
        -------
        values: List[TxnReturnType]
            Values returned in each calls inside transaction.
            If the call is `put` or `delete`, `None` will take that place.
        """
        if encoding is None:
            encoding = self.encoding
        txn = EtcdTransaction(self.channel, encoding=self.encoding)
        txn_builder(txn.success, txn.failure)
        return await txn.execute(compares)


class EtcdTransaction:

    channel: Channel
    encoding: str

    success: EtcdTransactionAction
    failure: EtcdTransactionAction

    def __init__(self, channel: Channel, encoding: str = 'utf-8'):
        self.encoding = encoding
        self.channel = channel

        self.success = EtcdTransactionAction(encoding=encoding)
        self.failure = EtcdTransactionAction(encoding=encoding)

    async def execute(
        self,
        compares: List[rpc_pb2.Compare],  # type: ignore
        encoding: Optional[str] = None,
    ):
        """
        Executes Txn and returns results.
        """
        if encoding is None:
            encoding = self.encoding
        txn_request = rpc_pb2.TxnRequest()
        txn_request.compare.extend(compares)
        for key in ('success', 'failure'):
            requests: List[TransactionRequest] = getattr(self, key).requests
            for request in requests:
                rop = rpc_pb2.RequestOp()
                if isinstance(request, PutRequestType):
                    rop.request_put.CopyFrom(request)
                elif isinstance(request, RangeRequestType):
                    rop.request_range.CopyFrom(request)
                elif isinstance(request, DeleteRangeRequestType):
                    rop.request_delete_range.CopyFrom(request)
                getattr(txn_request, key).extend([rop])
        stub = rpc_pb2_grpc.KVStub(self.channel)
        result = await stub.Txn(txn_request)

        ret: TxnReturnValues = []
        for response in result.responses:
            response_type = response.WhichOneof('response')
            if response_type == 'response_put':
                ret.append(None)  # TODO: Handle put response
            elif response_type == 'response_range':
                ret.append({
                    x.key.decode(encoding): x.value.decode(encoding)
                    for x in response.response_range.kvs
                })
            elif response_type == 'response_delete_range':
                ret.append(None)  # TODO: Handle delete response
            else:
                ret.append(None)
        return ret, result.succeeded


class EtcdTransactionAction:
    """
    Manages calls inside single transaction. `put`, `get` and `delete` calls are supported.
    """
    requests: List[TransactionRequest]
    encoding: str

    callback: Optional[Callable[[bool], None]] = None

    def __init__(self, encoding: str = 'utf-8'):
        self.requests = []
        self.encoding = encoding

    def add_callback(self, cb: Optional[Callable[[bool], None]]):
        self.callback = cb

    def put(
        self, key: str, value: Optional[str],
        lease: Optional[int] = None,
        ignore_value: bool = False,
        ignore_lease: bool = False,
        encoding: Optional[str] = None,
    ):
        """
        Puts given key into the key-value store.
        """
        if encoding is None:
            encoding = self.encoding
        self.requests.append(
            EtcdRequestGenerator.put(
                key, value,
                lease=lease, ignore_lease=ignore_lease,
                ignore_value=ignore_value, encoding=encoding,
            ),
        )

    def get(
        self, key: str,
        limit: Optional[str] = None,
        max_create_revision: Optional[str] = None,
        max_mod_revision: Optional[str] = None,
        min_create_revision: Optional[str] = None,
        min_mod_revision: Optional[str] = None,
        revision: Optional[str] = None,
        serializable: bool = True,
        sort_order: RangeRequestSortOrder = RangeRequestSortOrder.NONE,
        sort_target: RangeRequestSortTarget = RangeRequestSortTarget.KEY,
        encoding: Optional[str] = None,
    ):
        """
        Gets the keys in the range from the key-value store.
        """
        if encoding is None:
            encoding = self.encoding
        self.requests.append(
            EtcdRequestGenerator.get(
                key,
                limit=limit,
                max_create_revision=max_create_revision,
                max_mod_revision=max_mod_revision,
                min_create_revision=min_create_revision,
                min_mod_revision=min_mod_revision,
                revision=revision,
                serializable=serializable,
                sort_order=sort_order,
                sort_target=sort_target,
                encoding=encoding,
            ),
        )

    def delete(self, key: str, encoding: Optional[str] = None):
        """
        Deletes the given range from the key-value store.
        A delete request increments the revision of the key-value store
        and generates a delete event in the event history for every deleted key.
        """
        if encoding is None:
            encoding = self.encoding
        self.requests.append(EtcdRequestGenerator.delete(key, encoding=encoding))
