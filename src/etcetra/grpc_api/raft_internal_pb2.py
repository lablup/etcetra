# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: raft_internal.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from etcetra.grpc_api import gogo_pb2 as gogo__pb2
from etcetra.grpc_api import etcdserver_pb2 as etcdserver__pb2
from etcetra.grpc_api import rpc_pb2 as rpc__pb2
from etcetra.grpc_api import membership_pb2 as membership__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x13raft_internal.proto\x12\x0c\x65tcdserverpb\x1a\ngogo.proto\x1a\x10\x65tcdserver.proto\x1a\trpc.proto\x1a\x10membership.proto\"D\n\rRequestHeader\x12\n\n\x02ID\x18\x01 \x01(\x04\x12\x10\n\x08username\x18\x02 \x01(\t\x12\x15\n\rauth_revision\x18\x03 \x01(\x04\"\xd9\x0e\n\x13InternalRaftRequest\x12+\n\x06header\x18\x64 \x01(\x0b\x32\x1b.etcdserverpb.RequestHeader\x12\n\n\x02ID\x18\x01 \x01(\x04\x12!\n\x02v2\x18\x02 \x01(\x0b\x32\x15.etcdserverpb.Request\x12)\n\x05range\x18\x03 \x01(\x0b\x32\x1a.etcdserverpb.RangeRequest\x12%\n\x03put\x18\x04 \x01(\x0b\x32\x18.etcdserverpb.PutRequest\x12\x36\n\x0c\x64\x65lete_range\x18\x05 \x01(\x0b\x32 .etcdserverpb.DeleteRangeRequest\x12%\n\x03txn\x18\x06 \x01(\x0b\x32\x18.etcdserverpb.TxnRequest\x12\x33\n\ncompaction\x18\x07 \x01(\x0b\x32\x1f.etcdserverpb.CompactionRequest\x12\x34\n\x0blease_grant\x18\x08 \x01(\x0b\x32\x1f.etcdserverpb.LeaseGrantRequest\x12\x36\n\x0clease_revoke\x18\t \x01(\x0b\x32 .etcdserverpb.LeaseRevokeRequest\x12)\n\x05\x61larm\x18\n \x01(\x0b\x32\x1a.etcdserverpb.AlarmRequest\x12>\n\x10lease_checkpoint\x18\x0b \x01(\x0b\x32$.etcdserverpb.LeaseCheckpointRequest\x12\x35\n\x0b\x61uth_enable\x18\xe8\x07 \x01(\x0b\x32\x1f.etcdserverpb.AuthEnableRequest\x12\x37\n\x0c\x61uth_disable\x18\xf3\x07 \x01(\x0b\x32 .etcdserverpb.AuthDisableRequest\x12\x35\n\x0b\x61uth_status\x18\xf5\x07 \x01(\x0b\x32\x1f.etcdserverpb.AuthStatusRequest\x12@\n\x0c\x61uthenticate\x18\xf4\x07 \x01(\x0b\x32).etcdserverpb.InternalAuthenticateRequest\x12\x38\n\rauth_user_add\x18\xcc\x08 \x01(\x0b\x32 .etcdserverpb.AuthUserAddRequest\x12>\n\x10\x61uth_user_delete\x18\xcd\x08 \x01(\x0b\x32#.etcdserverpb.AuthUserDeleteRequest\x12\x38\n\rauth_user_get\x18\xce\x08 \x01(\x0b\x32 .etcdserverpb.AuthUserGetRequest\x12O\n\x19\x61uth_user_change_password\x18\xcf\x08 \x01(\x0b\x32+.etcdserverpb.AuthUserChangePasswordRequest\x12\x45\n\x14\x61uth_user_grant_role\x18\xd0\x08 \x01(\x0b\x32&.etcdserverpb.AuthUserGrantRoleRequest\x12G\n\x15\x61uth_user_revoke_role\x18\xd1\x08 \x01(\x0b\x32\'.etcdserverpb.AuthUserRevokeRoleRequest\x12:\n\x0e\x61uth_user_list\x18\xd2\x08 \x01(\x0b\x32!.etcdserverpb.AuthUserListRequest\x12:\n\x0e\x61uth_role_list\x18\xd3\x08 \x01(\x0b\x32!.etcdserverpb.AuthRoleListRequest\x12\x38\n\rauth_role_add\x18\xb0\t \x01(\x0b\x32 .etcdserverpb.AuthRoleAddRequest\x12>\n\x10\x61uth_role_delete\x18\xb1\t \x01(\x0b\x32#.etcdserverpb.AuthRoleDeleteRequest\x12\x38\n\rauth_role_get\x18\xb2\t \x01(\x0b\x32 .etcdserverpb.AuthRoleGetRequest\x12Q\n\x1a\x61uth_role_grant_permission\x18\xb3\t \x01(\x0b\x32,.etcdserverpb.AuthRoleGrantPermissionRequest\x12S\n\x1b\x61uth_role_revoke_permission\x18\xb4\t \x01(\x0b\x32-.etcdserverpb.AuthRoleRevokePermissionRequest\x12\x44\n\x13\x63luster_version_set\x18\x94\n \x01(\x0b\x32&.membershippb.ClusterVersionSetRequest\x12K\n\x17\x63luster_member_attr_set\x18\x95\n \x01(\x0b\x32).membershippb.ClusterMemberAttrSetRequest\x12\x42\n\x12\x64owngrade_info_set\x18\x96\n \x01(\x0b\x32%.membershippb.DowngradeInfoSetRequest\"\x0f\n\rEmptyResponse\"S\n\x1bInternalAuthenticateRequest\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x10\n\x08password\x18\x02 \x01(\t\x12\x14\n\x0csimple_token\x18\x03 \x01(\tB\x10\xc8\xe2\x1e\x01\xe0\xe2\x1e\x01\xd0\xe2\x1e\x01\xc8\xe1\x1e\x00\x62\x06proto3')



_REQUESTHEADER = DESCRIPTOR.message_types_by_name['RequestHeader']
_INTERNALRAFTREQUEST = DESCRIPTOR.message_types_by_name['InternalRaftRequest']
_EMPTYRESPONSE = DESCRIPTOR.message_types_by_name['EmptyResponse']
_INTERNALAUTHENTICATEREQUEST = DESCRIPTOR.message_types_by_name['InternalAuthenticateRequest']
RequestHeader = _reflection.GeneratedProtocolMessageType('RequestHeader', (_message.Message,), {
  'DESCRIPTOR' : _REQUESTHEADER,
  '__module__' : 'raft_internal_pb2'
  # @@protoc_insertion_point(class_scope:etcdserverpb.RequestHeader)
  })
_sym_db.RegisterMessage(RequestHeader)

InternalRaftRequest = _reflection.GeneratedProtocolMessageType('InternalRaftRequest', (_message.Message,), {
  'DESCRIPTOR' : _INTERNALRAFTREQUEST,
  '__module__' : 'raft_internal_pb2'
  # @@protoc_insertion_point(class_scope:etcdserverpb.InternalRaftRequest)
  })
_sym_db.RegisterMessage(InternalRaftRequest)

EmptyResponse = _reflection.GeneratedProtocolMessageType('EmptyResponse', (_message.Message,), {
  'DESCRIPTOR' : _EMPTYRESPONSE,
  '__module__' : 'raft_internal_pb2'
  # @@protoc_insertion_point(class_scope:etcdserverpb.EmptyResponse)
  })
_sym_db.RegisterMessage(EmptyResponse)

InternalAuthenticateRequest = _reflection.GeneratedProtocolMessageType('InternalAuthenticateRequest', (_message.Message,), {
  'DESCRIPTOR' : _INTERNALAUTHENTICATEREQUEST,
  '__module__' : 'raft_internal_pb2'
  # @@protoc_insertion_point(class_scope:etcdserverpb.InternalAuthenticateRequest)
  })
_sym_db.RegisterMessage(InternalAuthenticateRequest)

if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  DESCRIPTOR._serialized_options = b'\310\342\036\001\340\342\036\001\320\342\036\001\310\341\036\000'
  _REQUESTHEADER._serialized_start=96
  _REQUESTHEADER._serialized_end=164
  _INTERNALRAFTREQUEST._serialized_start=167
  _INTERNALRAFTREQUEST._serialized_end=2048
  _EMPTYRESPONSE._serialized_start=2050
  _EMPTYRESPONSE._serialized_end=2065
  _INTERNALAUTHENTICATEREQUEST._serialized_start=2067
  _INTERNALAUTHENTICATEREQUEST._serialized_end=2150
# @@protoc_insertion_point(module_scope)
