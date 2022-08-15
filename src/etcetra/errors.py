import functools
from typing import Any, Callable, ClassVar, Mapping, Optional

import grpc.aio

from .grpc_api import code_pb2


class EtcetraError(Exception):
    code: ClassVar[int]
    debug_map: Optional[Mapping[str, Any]]

    def __init__(self, message=None, debug_map=None):
        super().__init__(message)
        self.debug_map = debug_map

    def __int__(self):
        return self.code


class EtcdUnknownError(EtcetraError):
    code = code_pb2.UNKNOWN


class EtcdInvalidArgumentError(EtcetraError):
    code = code_pb2.INVALID_ARGUMENT


class EtcdDeadlineExceededError(EtcetraError):
    code = code_pb2.DEADLINE_EXCEEDED


class EtcdNotFoundError(EtcetraError):
    code = code_pb2.NOT_FOUND


class EtcdAlreadyExistsError(EtcetraError):
    code = code_pb2.ALREADY_EXISTS


class EtcdPermissionDeniedError(EtcetraError):
    code = code_pb2.PERMISSION_DENIED


class EtcdUnauthenticatedError(EtcetraError):
    code = code_pb2.UNAUTHENTICATED


class EtcdTooManyRequestError(EtcetraError):
    code = code_pb2.RESOURCE_EXHAUSTED


class EtcdBadRequestError(EtcetraError):
    code = code_pb2.FAILED_PRECONDITION


class EtcdAbortedError(EtcetraError):
    code = code_pb2.ABORTED


class EtcdOutOfRangeError(EtcetraError):
    code = code_pb2.OUT_OF_RANGE


class EtcdUnimplementedError(EtcetraError):
    code = code_pb2.UNIMPLEMENTED


class EtcdInternalError(EtcetraError):
    code = code_pb2.INTERNAL


class EtcdUnavailableError(EtcetraError):
    code = code_pb2.UNAVAILABLE


class EtcdDataLossError(EtcetraError):
    code = code_pb2.DATA_LOSS


def match_grpc_error(e: grpc.aio.AioRpcError):
    match e.code:
        case code_pb2.INVALID_ARGUMENT:
            return EtcdInvalidArgumentError(e.details(), debug_map=e.initial_metadata())
        case code_pb2.DEADLINE_EXCEEDED:
            return EtcdDeadlineExceededError(e.details(), debug_map=e.initial_metadata())
        case code_pb2.NOT_FOUND:
            return EtcdNotFoundError(e.details(), debug_map=e.initial_metadata())
        case code_pb2.ALREADY_EXISTS:
            return EtcdAlreadyExistsError(e.details(), debug_map=e.initial_metadata())
        case code_pb2.PERMISSION_DENIED:
            return EtcdPermissionDeniedError(e.details(), debug_map=e.initial_metadata())
        case code_pb2.UNAUTHENTICATED:
            return EtcdUnauthenticatedError(e.details(), debug_map=e.initial_metadata())
        case code_pb2.RESOURCE_EXHAUSTED:
            return EtcdTooManyRequestError(e.details(), debug_map=e.initial_metadata())
        case code_pb2.FAILED_PRECONDITION:
            return EtcdBadRequestError(e.details(), debug_map=e.initial_metadata())
        case code_pb2.ABORTED:
            return EtcdAbortedError(e.details(), debug_map=e.initial_metadata())
        case code_pb2.OUT_OF_RANGE:
            return EtcdOutOfRangeError(e.details(), debug_map=e.initial_metadata())
        case code_pb2.UNIMPLEMENTED:
            return EtcdUnimplementedError(e.details(), debug_map=e.initial_metadata())
        case code_pb2.INTERNAL:
            return EtcdInternalError(e.details(), debug_map=e.initial_metadata())
        case code_pb2.UNAVAILABLE:
            return EtcdUnavailableError(e.details(), debug_map=e.initial_metadata())
        case code_pb2.DATA_LOSS:
            return EtcdDataLossError(e.details(), debug_map=e.initial_metadata())
    return EtcdUnknownError(e.details(), debug_map=e.initial_metadata())


def grpc_exception_handler(outer: Callable):
    @functools.wraps(outer)
    async def wrapper(*args, **kwargs):
        try:
            return await outer(*args, **kwargs)
        except grpc.aio.AioRpcError as e:
            raise match_grpc_error(e) from e
    return wrapper
