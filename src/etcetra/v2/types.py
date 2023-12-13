from typing import Optional
from dataclasses import dataclass


@dataclass
class EtcdLockOption:
    lock_name: bytes
    timeout: Optional[float]
    ttl: Optional[int]
