from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AccessKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACCESS_KIND_UNSPECIFIED: _ClassVar[AccessKind]
    ACCESS_KIND_FREEDOM: _ClassVar[AccessKind]
    ACCESS_KIND_BRIDGE: _ClassVar[AccessKind]

class AccessLinkState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACCESS_LINK_STATE_UNSPECIFIED: _ClassVar[AccessLinkState]
    ACCESS_LINK_STATE_PENDING: _ClassVar[AccessLinkState]
    ACCESS_LINK_STATE_READY: _ClassVar[AccessLinkState]
    ACCESS_LINK_STATE_BLOCKED: _ClassVar[AccessLinkState]
    ACCESS_LINK_STATE_FAILED: _ClassVar[AccessLinkState]

class AccessBlockReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACCESS_BLOCK_REASON_UNSPECIFIED: _ClassVar[AccessBlockReason]
    ACCESS_BLOCK_REASON_TIME_EXPIRED: _ClassVar[AccessBlockReason]
    ACCESS_BLOCK_REASON_TRAFFIC_QUOTA_EXHAUSTED: _ClassVar[AccessBlockReason]
ACCESS_KIND_UNSPECIFIED: AccessKind
ACCESS_KIND_FREEDOM: AccessKind
ACCESS_KIND_BRIDGE: AccessKind
ACCESS_LINK_STATE_UNSPECIFIED: AccessLinkState
ACCESS_LINK_STATE_PENDING: AccessLinkState
ACCESS_LINK_STATE_READY: AccessLinkState
ACCESS_LINK_STATE_BLOCKED: AccessLinkState
ACCESS_LINK_STATE_FAILED: AccessLinkState
ACCESS_BLOCK_REASON_UNSPECIFIED: AccessBlockReason
ACCESS_BLOCK_REASON_TIME_EXPIRED: AccessBlockReason
ACCESS_BLOCK_REASON_TRAFFIC_QUOTA_EXHAUSTED: AccessBlockReason

class ApplyCustomerAccessRequest(_message.Message):
    __slots__ = ("customer_id", "vpn_fleet_id", "usage_quota_bytes", "expires_at_epoch_sec", "command_number")
    CUSTOMER_ID_FIELD_NUMBER: _ClassVar[int]
    VPN_FLEET_ID_FIELD_NUMBER: _ClassVar[int]
    USAGE_QUOTA_BYTES_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_EPOCH_SEC_FIELD_NUMBER: _ClassVar[int]
    COMMAND_NUMBER_FIELD_NUMBER: _ClassVar[int]
    customer_id: str
    vpn_fleet_id: int
    usage_quota_bytes: int
    expires_at_epoch_sec: int
    command_number: int
    def __init__(self, customer_id: _Optional[str] = ..., vpn_fleet_id: _Optional[int] = ..., usage_quota_bytes: _Optional[int] = ..., expires_at_epoch_sec: _Optional[int] = ..., command_number: _Optional[int] = ...) -> None: ...

class ApplyCustomerAccessResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetCustomerAccessLinksRequest(_message.Message):
    __slots__ = ("customer_id",)
    CUSTOMER_ID_FIELD_NUMBER: _ClassVar[int]
    customer_id: str
    def __init__(self, customer_id: _Optional[str] = ...) -> None: ...

class CustomerAccessLink(_message.Message):
    __slots__ = ("kind", "state", "block_reason", "uri")
    KIND_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    BLOCK_REASON_FIELD_NUMBER: _ClassVar[int]
    URI_FIELD_NUMBER: _ClassVar[int]
    kind: AccessKind
    state: AccessLinkState
    block_reason: AccessBlockReason
    uri: str
    def __init__(self, kind: _Optional[_Union[AccessKind, str]] = ..., state: _Optional[_Union[AccessLinkState, str]] = ..., block_reason: _Optional[_Union[AccessBlockReason, str]] = ..., uri: _Optional[str] = ...) -> None: ...

class GetCustomerAccessLinksResponse(_message.Message):
    __slots__ = ("links",)
    LINKS_FIELD_NUMBER: _ClassVar[int]
    links: _containers.RepeatedCompositeFieldContainer[CustomerAccessLink]
    def __init__(self, links: _Optional[_Iterable[_Union[CustomerAccessLink, _Mapping]]] = ...) -> None: ...
