from __future__ import annotations
from collections import namedtuple

from dataclasses import dataclass, field
import enum
from typing import Any, List, Mapping, Optional, Union, TYPE_CHECKING
if TYPE_CHECKING:
    from typing_extensions import TypeAlias

from etcetra.grpc_api import rpc_pb2

__all__ = (
    'RangeRequestSortOrder',
    'RangeRequestSortTarget',
    'WatchCreateRequestFilterType',
    'CompareCompareResult',
    'CompareCompareTarget',
    'WatchEventType',
    'CompareKey',
    'CompareBuilder',
    'EtcdCredential',
    'EtcdLockOption',
    'HostPortPair',
    'WatchEvent',
    'PutRequestType',
    'RangeRequestType',
    'DeleteRangeRequestType',
    'TransactionRequest',
    'NoneType',
    'TxnReturnValues',
    'TxnReturnType',
)


class RangeRequestSortOrder(enum.Enum):
    NONE = 0
    ASCEND = 1
    DESCEND = 2


class RangeRequestSortTarget(enum.Enum):
    KEY = 0
    VERSION = 1
    CREATE = 2
    MOD = 3
    VALUE = 4


class WatchCreateRequestFilterType(enum.Enum):
    NOPUT = 0
    NODELETE = 1


class CompareCompareResult(enum.Enum):
    EQUAL = 0
    GREATER = 1
    LESS = 2
    NOT_EQUAL = 3


class CompareCompareTarget(enum.Enum):
    VERSION = 0
    CREATE = 1
    MOD = 2
    VALUE = 3
    LEASE = 4


class WatchEventType(enum.Enum):
    PUT = 0
    DELETE = 1


PutRequestType = rpc_pb2.PutRequest
RangeRequestType = rpc_pb2.RangeRequest
DeleteRangeRequestType = rpc_pb2.DeleteRangeRequest
TransactionRequest = Union[PutRequestType, RangeRequestType, DeleteRangeRequestType]  # type: ignore
NoneType = type(None)
TxnReturnValues: TypeAlias = List[Union[Mapping[str, str], NoneType]]
TxnReturnType = namedtuple('TxnReturnType', ['values', 'success'])


@dataclass
class CompareKey:
    key: str

    target_lease: Optional[int] = field(default=None)
    mod_revision: Optional[int] = field(default=None)
    range_end: Optional[str] = field(default=None)
    target_version: Optional[int] = field(default=None)
    encoding: str = field(default='utf-8')

    @property
    def version(self):
        return CompareBuilder(self, CompareCompareTarget.VERSION)

    @property
    def create(self):
        return CompareBuilder(self, CompareCompareTarget.CREATE)

    @property
    def mod(self):
        return CompareBuilder(self, CompareCompareTarget.MOD)

    @property
    def value(self):
        return CompareBuilder(self, CompareCompareTarget.VALUE)

    @property
    def lease(self):
        return CompareBuilder(self, CompareCompareTarget.LEASE)


@dataclass
class CompareBuilder:
    key: CompareKey
    target: CompareCompareTarget

    def build_request(self, other: Any, result: CompareCompareResult):
        value: bytes | int
        if isinstance(other, str):
            value = other.encode(self.key.encoding)
        elif isinstance(other, int):
            value = other
        else:
            raise ValueError('rhs is not a str or int')
        lease = self.key.target_lease
        mod_revision = self.key.mod_revision
        range_end = self.key.range_end
        version = self.key.target_version

        return rpc_pb2.Compare(
            key=self.key.key.encode(self.key.encoding), value=value,
            result=result.value, target=self.target.value,
            lease=str(lease) if lease is not None else None,
            mod_revision=str(mod_revision) if mod_revision is not None else None,
            range_end=range_end.encode(self.key.encoding) if range_end is not None else None,
            version=str(version) if version is not None else None,
        )

    def __eq__(self, other: object):
        return self.build_request(other, CompareCompareResult.EQUAL)

    def __ne__(self, other: object):
        return self.build_request(other, CompareCompareResult.NOT_EQUAL)

    def __gt__(self, other: object):
        return self.build_request(other, CompareCompareResult.GREATER)

    def __lt__(self, other: object):
        return self.build_request(other, CompareCompareResult.GREATER)


@dataclass
class EtcdCredential:
    username: str
    password: str


@dataclass
class HostPortPair:
    host: str
    port: int

    def __str__(self):
        return f'{self.host}:{self.port}'

    @classmethod
    def parse(cls, s: str) -> HostPortPair:
        if ':' in s:
            host, port_str = s.rsplit(':')
            port = int(port_str)
        else:
            host = s
            port = 2379
        return cls(host, port)


@dataclass(unsafe_hash=True)
class WatchEvent:
    key: str
    value: Optional[str]
    prev_value: Optional[str]
    event: WatchEventType


@dataclass
class EtcdLockOption:
    lock_name: str
    timeout: Optional[float]
    ttl: Optional[int]
