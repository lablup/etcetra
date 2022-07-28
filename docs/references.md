# Welcome to etcetra’s documentation!

Pure python asyncio Etcd client.


### _class_ etcetra.client.EtcdClient(addr: HostPortPair, credentials: Optional[EtcdCredential] = None, secure: bool = False, encoding: str = 'utf-8')
Wrapper class of underlying actual Etcd API implementations (KV, Watch, Txn, …).
In most cases, user can perform most of the jobs by creating EtcdClient object.


#### connect()
Async context manager which establishes connection to Etcd cluster.


* **Returns**

    **communicator** – An EtcdCommunicator instance.



* **Return type**

    EtcdCommunicator



#### with_lock(lock_name: str, timeout: Optional[float] = None, ttl: Optional[int] = None)
Async context manager which establishes connection and then
immediately tries to acquire lock with given lock name.
Acquired lock will automatically released when user exits with context.


* **Parameters**

    
    * **lock_name** – Name of Etcd lock to acquire.


    * **timeout** – Number of seconds to wait until lock is acquired. Defaults to None.
    If value is None, with_lock will wait forever until lock is acquired.


    * **ttl** – If not None, sets a TTL to granted Lock.
    The lock will be automatically released after this amount of seconds elapses.
    Defaults to None.



* **Returns**

    **communicator** – An EtcdCommunicator instance.



* **Return type**

    EtcdCommunicator



* **Raises**

    **asyncio.TimeoutError** – When timeout expires.



### _class_ etcetra.client.EtcdCommunicator(channel: Channel, encoding: str = 'utf-8')
Performs actual API calls to Etcd cluster and returns result.


#### _async_ campaign_election(name: bytes, lease_id: int, value: Optional[bytes] = None)
Campaign waits to acquire leadership in an election,
returning a LeaderKey representing the leadership if successful.
The LeaderKey can then be used to issue new values on the election,
transactionally guard API requests on leadership still being held,
and resign from the election.


* **Parameters**

    
    * **name** – Name is the election’s identifier for the campaign.


    * **lease_id** – LeaseID is the ID of the lease attached to leadership of the election.
    If the lease expires or is revoked before resigning leadership,
    then the leadership is transferred to the next campaigner, if any.


    * **value** – Value is the initial proclaimed value set when the campaigner wins the election.



* **Returns**

    **leader** – Leader describes the resources used for holding leadereship of the election.



* **Return type**

    etcetra.grpc_api.v3election_pb2.LeaderKey



#### create_lease_keepalive_task(id: int, interval: float)
Creates asyncio Task which sends Keepalive request to given lease ID.


* **Parameters**

    
    * **id** – Lease ID to send Keepalive request.


    * **interval** – Interval to send Keepalive request.



* **Returns**

    **task**



* **Return type**

    asyncio.Task



#### _async_ delete(key: str, prev_kv: bool = False, encoding: Optional[str] = None)
Deletes the given key the key-value store.
A delete request increments the revision of the key-value store
and generates a delete event in the event history for every deleted key.


* **Parameters**

    
    * **key** – The key to delete.


    * **prev_kv** – If this value set to True and previous value with associated target key exists,
    this method will return previous value.


    * **encoding** – Character encoding type to encode/decode all types of byte based strings.
    If this value is None, this method will use default encoding which is set when creating
    this instance.
    Defaults to utf-8.



* **Returns**

    **value** – If prev_kv is set to True and previous value exists, returns previous value.
    Otherwise it will just return None.



* **Return type**

    Optional[str]



#### _async_ delete_prefix(key: str, prev_kv: bool = False, encoding: Optional[str] = None)
Deletes keys with given prefix and its associated values from the key-value store.
A delete request increments the revision of the key-value store
and generates a delete event in the event history for every deleted key.


* **Parameters**

    
    * **key** – The key prefix to delete.


    * **prev_kv** – If this value set to True and previous value with associated target key exists,
    this method will return previous value.


    * **encoding** – Character encoding type to encode/decode all types of byte based strings.
    If this value is None, this method will use default encoding which is set when creating
    this instance.
    Defaults to utf-8.



* **Returns**

    **values** – If prev_kv is set to True and previous value exists, returns previous value.
    Otherwise it will just return None.



* **Return type**

    Optional[List[Optional[str]]]



#### _async_ delete_range(key: str, range_end: str, prev_kv: bool = False, encoding: Optional[str] = None)
Deletes the given range from the key-value store.
A delete request increments the revision of the key-value store
and generates a delete event in the event history for every deleted key.


* **Parameters**

    
    * **key** – Start of key range.


    * **range_end** – End of key range.


    * **prev_kv** – If this value set to True and previous value with associated target key exists,
    this method will return previous value.


    * **encoding** – Character encoding type to encode/decode all types of byte based strings.
    If this value is None, this method will use default encoding which is set when creating
    this instance.
    Defaults to utf-8.



* **Returns**

    **values** – If prev_kv is set to True and previous value exists, returns previous value.
    Otherwise it will just return None.



* **Return type**

    Optional[str]



#### _async_ get(key: str, max_create_revision: Optional[str] = None, max_mod_revision: Optional[str] = None, min_create_revision: Optional[str] = None, min_mod_revision: Optional[str] = None, revision: Optional[str] = None, encoding: Optional[str] = None)
Gets value associated with given key from the key-value store.


* **Parameters**

    
    * **key** – The key to look up.


    * **max_create_revision** – The upper bound for returned key create revisions;
    all keys with greater create revisions will be filtered away.


    * **max_mod_revision** – The upper bound for returned key mod revisions;
    all keys with greater mod revisions will be filtered away.


    * **min_create_revision** – The lower bound for returned key create revisions;
    all keys with lesser create revisions will be filtered away.


    * **min_mod_revision** – The lower bound for returned key mod revisions;
    all keys with lesser mod revisions will be filtered away.


    * **revision** – The point-in-time of the key-value store to use for the range.
    If revision is less or equal to zero, the range is over the newest key-value store.
    If the revision has been compacted, ErrCompacted is returned as a response.


    * **encoding** – Character encoding type to encode/decode all types of byte based strings.
    If this value is None, this method will use default encoding which is set when creating
    this instance.
    Defaults to utf-8.



* **Returns**

    **value** – Returns value if given key exists. Otherwise it will return None.



* **Return type**

    Optional[str]



#### _async_ get_election(name: bytes)
Returns the current election proclamation, if any.


* **Parameters**

    **name** – Name is the election identifier for the leadership information.



* **Returns**

    KV is the key-value pair representing the latest leader update



* **Return type**

    kv



#### _async_ get_prefix(key: str, max_create_revision: Optional[str] = None, max_mod_revision: Optional[str] = None, min_create_revision: Optional[str] = None, min_mod_revision: Optional[str] = None, revision: Optional[str] = None, sort_order: RangeRequestSortOrder = RangeRequestSortOrder.NONE, sort_target: RangeRequestSortTarget = RangeRequestSortTarget.KEY, encoding: Optional[str] = None)
Gets the key-value in dictionary from the key-value store with given key prefix.
i.e. get_prefix(‘/sorna/local’) call looks up all keys which has /sorna/local prefix.


* **Parameters**

    
    * **key** – The key prefix to look up.


    * **max_create_revision** – The upper bound for returned key create revisions;
    all keys with greater create revisions will be filtered away.


    * **max_mod_revision** – The upper bound for returned key mod revisions;
    all keys with greater mod revisions will be filtered away.


    * **min_create_revision** – The lower bound for returned key create revisions;
    all keys with lesser create revisions will be filtered away.


    * **min_mod_revision** – The lower bound for returned key mod revisions;
    all keys with lesser mod revisions will be filtered away.


    * **revision** – The point-in-time of the key-value store to use for the range.
    If revision is less or equal to zero, the range is over the newest key-value store.
    If the revision has been compacted, ErrCompacted is returned as a response.


    * **sort_order** – Sort order. Defaults to RangeRequestSortOrder.NONE.


    * **sort_target** – Sort target. Defaults to RangeRequestSortTarget.KEY.


    * **encoding** – Character encoding type to encode/decode all types of byte based strings.
    If this value is None, this method will use default encoding which is set when creating
    this instance.
    Defaults to utf-8.



* **Returns**

    **value** – Returns dictionary with all key-values which matches given key prefix.



* **Return type**

    Mapping[str, str]



#### _async_ get_range(key: str, range_end: str, limit: Optional[str] = None, max_create_revision: Optional[str] = None, max_mod_revision: Optional[str] = None, min_create_revision: Optional[str] = None, min_mod_revision: Optional[str] = None, revision: Optional[str] = None, sort_order: RangeRequestSortOrder = RangeRequestSortOrder.NONE, sort_target: RangeRequestSortTarget = RangeRequestSortTarget.KEY, encoding: Optional[str] = None)
Gets the key-value in dictionary from the key-value store with keys in [key, range_end) range.


* **Parameters**

    
    * **key** – Start of key range.


    * **range_end** – End of key range.


    * **max_create_revision** – The upper bound for returned key create revisions;
    all keys with greater create revisions will be filtered away.


    * **max_mod_revision** – The upper bound for returned key mod revisions;
    all keys with greater mod revisions will be filtered away.


    * **min_create_revision** – The lower bound for returned key create revisions;
    all keys with lesser create revisions will be filtered away.


    * **min_mod_revision** – The lower bound for returned key mod revisions;
    all keys with lesser mod revisions will be filtered away.


    * **revision** – The point-in-time of the key-value store to use for the range.
    If revision is less or equal to zero, the range is over the newest key-value store.
    If the revision has been compacted, ErrCompacted is returned as a response.


    * **sort_order** – Sort order. Defaults to RangeRequestSortOrder.NONE.


    * **sort_target** – Sort target. Defaults to RangeRequestSortTarget.KEY.


    * **encoding** – Character encoding type to encode/decode all types of byte based strings.
    If this value is None, this method will use default encoding which is set when creating
    this instance.
    Defaults to utf-8.



* **Returns**

    **value** – Returns dictionary with all key-values which matches given key prefix.



* **Return type**

    Mapping[str, str]



#### _async_ grant_lease(ttl: int, id: Optional[int] = None)
Creates a lease which expires if the server does not receive a keepAlive
within a given time to live period. All keys attached to the lease
will be expired and deleted if the lease expires.
Each expired key generates a delete event in the event history.


* **Parameters**

    
    * **ttl** – Advisory time-to-live in seconds.


    * **id** – Requested ID for the lease. If ID is set to None, the lessor chooses an ID.



* **Returns**

    **id** – Lease ID for the granted lease.



* **Return type**

    int



#### _async_ keys_prefix(key: str, max_create_revision: Optional[str] = None, max_mod_revision: Optional[str] = None, min_create_revision: Optional[str] = None, min_mod_revision: Optional[str] = None, revision: Optional[str] = None, sort_order: RangeRequestSortOrder = RangeRequestSortOrder.NONE, sort_target: RangeRequestSortTarget = RangeRequestSortTarget.KEY, encoding: Optional[str] = None)
Gets the keys which has given prefix from the key-value store.


* **Parameters**

    
    * **key** – The key prefix to look up.


    * **max_create_revision** – The upper bound for returned key create revisions;
    all keys with greater create revisions will be filtered away.


    * **max_mod_revision** – The upper bound for returned key mod revisions;
    all keys with greater mod revisions will be filtered away.


    * **min_create_revision** – The lower bound for returned key create revisions;
    all keys with lesser create revisions will be filtered away.


    * **min_mod_revision** – The lower bound for returned key mod revisions;
    all keys with lesser mod revisions will be filtered away.


    * **revision** – The point-in-time of the key-value store to use for the range.
    If revision is less or equal to zero, the range is over the newest key-value store.
    If the revision has been compacted, ErrCompacted is returned as a response.


    * **sort_order** – Sort order. Defaults to RangeRequestSortOrder.NONE.


    * **sort_target** – Sort target. Defaults to RangeRequestSortTarget.KEY.


    * **encoding** – Character encoding type to encode/decode all types of byte based strings.
    If this value is None, this method will use default encoding which is set when creating
    this instance.
    Defaults to utf-8.



* **Returns**

    **keys** – Returns list of found keys.



* **Return type**

    List[str]



#### _async_ keys_range(key: str, range_end: str, limit: Optional[str] = None, max_create_revision: Optional[str] = None, max_mod_revision: Optional[str] = None, min_create_revision: Optional[str] = None, min_mod_revision: Optional[str] = None, revision: Optional[str] = None, serializable: bool = True, sort_order: RangeRequestSortOrder = RangeRequestSortOrder.NONE, sort_target: RangeRequestSortTarget = RangeRequestSortTarget.KEY, encoding: Optional[str] = None)
Gets the keys in the range from the key-value store.


* **Parameters**

    
    * **key** – Start of key range.


    * **range_end** – End of key range.


    * **max_create_revision** – The upper bound for returned key create revisions;
    all keys with greater create revisions will be filtered away.


    * **max_mod_revision** – The upper bound for returned key mod revisions;
    all keys with greater mod revisions will be filtered away.


    * **min_create_revision** – The lower bound for returned key create revisions;
    all keys with lesser create revisions will be filtered away.


    * **min_mod_revision** – The lower bound for returned key mod revisions;
    all keys with lesser mod revisions will be filtered away.


    * **revision** – The point-in-time of the key-value store to use for the range.
    If revision is less or equal to zero, the range is over the newest key-value store.
    If the revision has been compacted, ErrCompacted is returned as a response.


    * **sort_order** – Sort order. Defaults to RangeRequestSortOrder.NONE.


    * **sort_target** – Sort target. Defaults to RangeRequestSortTarget.KEY.


    * **encoding** – Character encoding type to encode/decode all types of byte based strings.
    If this value is None, this method will use default encoding which is set when creating
    this instance.
    Defaults to utf-8.



* **Returns**

    **keys** – Returns list of found keys.



* **Return type**

    List[str]



#### _async_ observe_election(name: bytes)
Observe streams election proclamations in-order as made by the election’s elected leaders.


* **Parameters**

    **name** – Name is the election identifier for the leadership information.



* **Returns**

    **event** – A Leader object containing event information.



* **Return type**

    AsyncIterator[Leader]



#### _async_ proclaim_election(leader: LeaderKey, value: bytes)
Proclaim updates the leader’s posted value with a new value.


* **Parameters**

    
    * **leader** – Leader is the leadership hold on the election.


    * **value** – Value is an update meant to overwrite the leader’s current value.



#### _async_ put(key: str, value: Optional[str], lease: Optional[int] = None, prev_kv: bool = False, encoding: Optional[str] = None)
Puts given key into the key-value store.


* **Parameters**

    
    * **key** – The key to put into the key-value store


    * **value** – The value to associate with the key in the key-value store.


    * **lease** – The lease ID to associate with the key in the key-value store. Defaults to None.
    None lease indicates no lease.


    * **prev_kv** – If this value is True, gets the previous value before changing it and returns it.
    Defaults to False.


    * **encoding** – Character encoding type to encode/decode all types of byte based strings.
    If this value is None, this method will use default encoding which is set when creating
    this instance.
    Defaults to utf-8.



* **Returns**

    **value** – If prev_kv is set to True and previous value exists, returns previous value.
    Otherwise it will just return None.



* **Return type**

    Optional[str]



#### _async_ resign_election(leader: LeaderKey)
Resign releases election leadership so other campaigners may acquire leadership on the election.


* **Parameters**

    **leader** – Leader is the leadership to relinquish by resignation.



#### _async_ revoke_lease(id: int)
Revokes a lease. All keys attached to the lease will expire and be deleted.


* **Parameters**

    **id** – Lease ID to revoke. When the ID is revoked, all associated keys will be deleted.



#### _async_ txn(txn_builder: Callable[[EtcdTransactionAction], None], encoding: Optional[str] = None)
A shorthand helper for Txn, with no compare arguments.
This can be helpful when user just wants to execute transaction without
any conditions.

```python
>>> await communicator.put('/tmp/successkey', '1111')
>>> def _txn_builder(action):
...     action.get('/tmp/successkey')
...
>>> values = await communicator.txn(_txn_builder)
>>> print(values)  # ['1111']
```


* **Parameters**

    
    * **txn_builder** – Function which accepts EtcdTransactionAction as argument and performs
    all KV calls.


    * **encoding** – Character encoding type to encode/decode all types of byte based strings.
    If this value is None, this method will use default encoding which is set when creating
    this instance.
    Defaults to utf-8.



* **Returns**

    **values** – Values returned in each calls inside transaction.
    If the call is put or delete, None will take that place.



* **Return type**

    List[TxnReturnType]



#### _async_ txn_compare(compares: List[Compare], txn_builder: Callable[[EtcdTransactionAction, EtcdTransactionAction], None], encoding: Optional[str] = None)
Processes multiple requests in a single transaction.
A txn request increments the revision of the key-value store
and generates events with the same revision for every completed request.
It is not allowed to modify the same key several times within one txn.

```python
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
```


* **Parameters**

    
    * **compare** – List of predicates representing a conjunction of terms.
    If the comparisons succeed, then the success requests will be processed in order,
    and the response will contain their respective responses in order.
    If the comparisons fail, then the failure requests will be processed in order,
    and the response will contain their respective responses in order.


    * **txn_builder** – Function which accepts EtcdTransactionAction as argument and performs
    all KV calls.


    * **encoding** – Character encoding type to encode/decode all types of byte based strings.
    If this value is None, this method will use default encoding which is set when creating
    this instance.
    Defaults to utf-8.



* **Returns**

    **values** – Values returned in each calls inside transaction.
    If the call is put or delete, None will take that place.



* **Return type**

    List[TxnReturnType]



#### watch(key: str, ready_event: Optional[Event] = None, filters: Optional[List[WatchCreateRequestFilterType]] = None, prev_kv: bool = False, progress_notify: bool = False, start_revision: Optional[int] = None, watch_id: Optional[int] = None, encoding: Optional[str] = None)
Async iterator which watches for events happening or that have happened.
Both input and output are streams; the input stream is for creating and canceling watchers
and the output stream sends events.
One watch RPC can watch on multiple key ranges, streaming events for several watches at once.
The entire event history can be watched starting from the last compaction revision.


* **Parameters**

    
    * **key** – The key to watch events.


    * **ready_event** – If this value is set, Event.set() will be called
    when watch is ready to accept events.


    * **filters** – Events to filter. Defaults to None.
    If this list is None, watch will yield all types of event.


    * **prev_kv** – If this value is set to True, event will be yielded with previous value supplied.


    * **progress_notify** – progress_notify is set so that the etcd server will periodically send a WatchResponse
    with no events to the new watcher if there are no recent events.
    It is useful when clients wish to recover a disconnected watcher
    starting from a recent known revision.
    The etcd server may decide how often it will send notifications based on current load.


    * **start_revision** – An optional revision to watch from (inclusive). No start_revision is “now”.


    * **watch_id** – If watch_id is provided and non-zero, it will be assigned to this watcher.
    Since creating a watcher in etcd is not a synchronous operation,
    this can be used ensure that ordering is correct
    when creating multiple watchers on the same stream.
    Creating a watcher with an ID already in use on the stream
    will cause an error to be returned.


    * **encoding** – Character encoding type to encode/decode all types of byte based strings.
    If this value is None, this method will use default encoding which is set when creating
    this instance.
    Defaults to utf-8.



* **Returns**

    **event** – A WatchEvent object containing event information.



* **Return type**

    AsyncIterator[WatchEvent]



#### watch_prefix(key: str, ready_event: Optional[Event] = None, filters: Optional[List[WatchCreateRequestFilterType]] = None, prev_kv: bool = False, progress_notify: bool = True, start_revision: Optional[int] = None, watch_id: Optional[int] = None, encoding: Optional[str] = None)
Watches for events happening or that have happened along keys with given prefix.
Both input and output are streams; the input stream is for creating and canceling watchers
and the output stream sends events.
One watch RPC can watch on multiple key ranges, streaming events for several watches at once.
The entire event history can be watched starting from the last compaction revision.


* **Parameters**

    
    * **key** – The key prefix to watch events.


    * **ready_event** – If this value is set, Event.set() will be called
    when watch is ready to accept events.


    * **filters** – Events to filter. Defaults to None.
    If this list is None, watch will yield all types of event.


    * **prev_kv** – If this value is set to True, event will be yielded with previous value supplied.


    * **progress_notify** – progress_notify is set so that the etcd server will periodically send a WatchResponse
    with no events to the new watcher if there are no recent events.
    It is useful when clients wish to recover a disconnected watcher
    starting from a recent known revision.
    The etcd server may decide how often it will send notifications based on current load.


    * **start_revision** – An optional revision to watch from (inclusive). No start_revision is “now”.


    * **watch_id** – If watch_id is provided and non-zero, it will be assigned to this watcher.
    Since creating a watcher in etcd is not a synchronous operation,
    this can be used ensure that ordering is correct
    when creating multiple watchers on the same stream.
    Creating a watcher with an ID already in use on the stream
    will cause an error to be returned.


    * **encoding** – Character encoding type to encode/decode all types of byte based strings.
    If this value is None, this method will use default encoding which is set when creating
    this instance.
    Defaults to utf-8.



* **Returns**

    **event** – A WatchEvent object containing event information.



* **Return type**

    AsyncIterator[WatchEvent]



### _class_ etcetra.client.EtcdTransactionAction(encoding: str = 'utf-8')
Manages calls inside single transaction. put, get and delete calls are supported.


#### delete(key: str, encoding: Optional[str] = None)
Deletes the given range from the key-value store.
A delete request increments the revision of the key-value store
and generates a delete event in the event history for every deleted key.


#### get(key: str, limit: Optional[str] = None, max_create_revision: Optional[str] = None, max_mod_revision: Optional[str] = None, min_create_revision: Optional[str] = None, min_mod_revision: Optional[str] = None, revision: Optional[str] = None, serializable: bool = True, sort_order: RangeRequestSortOrder = RangeRequestSortOrder.NONE, sort_target: RangeRequestSortTarget = RangeRequestSortTarget.KEY, encoding: Optional[str] = None)
Gets the keys in the range from the key-value store.


#### put(key: str, value: Optional[str], lease: Optional[int] = None, ignore_value: bool = False, ignore_lease: bool = False, encoding: Optional[str] = None)
Puts given key into the key-value store.


### _class_ etcetra.types.CompareBuilder(key: 'CompareKey', target: 'CompareCompareTarget')

### _class_ etcetra.types.CompareCompareResult(value)
An enumeration.


### _class_ etcetra.types.CompareCompareTarget(value)
An enumeration.


### _class_ etcetra.types.CompareKey(key: 'str', target_lease: 'Optional[int]' = None, mod_revision: 'Optional[int]' = None, range_end: 'Optional[str]' = None, target_version: 'Optional[int]' = None, encoding: 'str' = 'utf-8')

### etcetra.types.DeleteRangeRequestType()
alias of `DeleteRangeRequest`


### _class_ etcetra.types.EtcdCredential(username: 'str', password: 'str')

### _class_ etcetra.types.EtcdLockOption(lock_name: 'str', timeout: 'Optional[float]', ttl: 'Optional[int]')

### _class_ etcetra.types.HostPortPair(host: 'str', port: 'int')

### etcetra.types.PutRequestType()
alias of `PutRequest`


### _class_ etcetra.types.RangeRequestSortOrder(value)
An enumeration.


### _class_ etcetra.types.RangeRequestSortTarget(value)
An enumeration.


### etcetra.types.RangeRequestType()
alias of `RangeRequest`


### _class_ etcetra.types.TxnReturnType(values, success)

#### success(_: boo_ )
Alias for field number 1


#### values(_: List[Optional[Mapping[str, str]]_ )
Alias for field number 0


### _class_ etcetra.types.WatchCreateRequestFilterType(value)
An enumeration.


### _class_ etcetra.types.WatchEvent(key: 'str', value: 'Optional[str]', prev_value: 'Optional[str]', event: 'WatchEventType')

### _class_ etcetra.types.WatchEventType(value)
An enumeration.

# Indices and tables


* [Index](genindex.md)


* [Module Index](py-modindex.md)


* [Search Page](search.md)
