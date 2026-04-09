"""Minimal MQTT/UDP client."""

import socket
from collections.abc import Iterator
from enum import IntEnum
from typing import Literal, NamedTuple, Self, overload

__all__ = ["Client", "Packet", "PacketType", "match_topic"]

MIN_PACKET_BYTES = 2
PACKET_ID_BYTES = 2
TOPIC_LENGTH_BYTES = 2
MAX_TOPIC_BYTES = 0xFFFF


def match_topic(topic_filter: str, topic: str, /) -> bool:
    """Check if a topic name matches a topic filter."""
    topic_parts = topic.split("/")
    filter_parts = topic_filter.split("/")
    index = 0
    while index < len(filter_parts):
        if index >= len(topic_parts):
            return False
        if filter_parts[index] == "#":
            return True
        if filter_parts[index] in ("+", topic_parts[index]):
            index += 1
        else:
            return False

    return index == len(topic_parts)


class PacketType(IntEnum):
    """MQTT/UDP packet types."""

    PUBLISH = 3
    PUBACK = 4
    SUBSCRIBE = 8
    PINGREQ = 12
    PINGRESP = 13

    def __str__(self) -> str:
        """Return the name of this packet type."""
        return self.name


class Packet(NamedTuple):
    """An MQTT/UDP packet."""

    type: PacketType | int
    """Packet type."""
    qos: int | None
    """QoS level."""
    dup: bool | None
    """Whether this packet is a retransmission."""
    identifier: int | None
    """Packet identifier."""
    topic: str | None
    """MQTT topic."""
    payload: bytes
    """MQTT payload."""
    src_addr: tuple[str, int]
    """Source IP address and port."""


def _encode_remaining_length(length: int, /) -> bytes:
    if length < 0:
        msg = "remaining length must be non-negative"
        raise ValueError(msg)

    encoded = bytearray()
    remaining = length
    while True:
        byte = remaining % 128
        remaining //= 128
        if remaining > 0:
            byte |= 128
        encoded.append(byte)
        if remaining == 0:
            return bytes(encoded)


def _encode_packet_id(packet_id: int, /) -> bytes:
    return packet_id.to_bytes(PACKET_ID_BYTES, "big")


def _encode_topic(topic: str, /) -> bytes:
    if not topic:
        msg = "topic must not be empty"
        raise ValueError(msg)

    topic_bytes = topic.encode("utf-8")
    if len(topic_bytes) > MAX_TOPIC_BYTES:
        msg = "topic is too long"
        raise ValueError(msg)

    return len(topic_bytes).to_bytes(TOPIC_LENGTH_BYTES, "big") + topic_bytes


def _encode_packet(packet_type: PacketType, /, *, flags: int = 0, body: bytes = b"") -> bytes:
    return bytes([(packet_type.value << 4) | (flags & 0b1111)]) + _encode_remaining_length(len(body)) + body


def _decode_remaining_length(packet: bytes, /, *, start: int = 1) -> tuple[int, int]:
    multiplier = 1
    value = 0
    index = start
    packet_len = len(packet)

    for _ in range(4):
        if index >= packet_len:
            msg = "missing remaining length bytes"
            raise ValueError(msg)
        byte = packet[index]
        index += 1
        value += (byte & 127) * multiplier
        multiplier *= 128
        if (byte & 128) == 0:
            return value, index

    msg = "malformed remaining length"
    raise ValueError(msg)


def _decode_packet_id(body: bytes, /, *, start: int = 0) -> tuple[int, int]:
    end = start + PACKET_ID_BYTES
    if end > len(body):
        msg = "packet missing identifier"
        raise ValueError(msg)

    packet_id = int.from_bytes(body[start:end], "big")
    return packet_id, end


def _decode_topic(body: bytes, /, *, start: int = 0) -> tuple[str, int]:
    len_end = start + TOPIC_LENGTH_BYTES
    if len_end > len(body):
        msg = "packet missing topic length"
        raise ValueError(msg)

    topic_len = int.from_bytes(body[start:len_end], "big")
    if topic_len == 0:
        msg = "topic must not be empty"
        raise ValueError(msg)

    topic_end = len_end + topic_len
    if topic_end > len(body):
        msg = "topic exceeds packet size"
        raise ValueError(msg)

    try:
        topic = body[len_end:topic_end].decode("utf-8")
    except UnicodeDecodeError as exc:
        msg = "topic is not valid utf-8"
        raise ValueError(msg) from exc

    return topic, topic_end


def _decode_packet(packet: bytes, /, *, src_addr: tuple[str, int]) -> Packet:
    if len(packet) < MIN_PACKET_BYTES:
        msg = "packet is too short"
        raise ValueError(msg)

    packet_type = packet[0] >> 4
    if packet_type in PacketType:
        packet_type = PacketType(packet_type)

    flags = packet[0] & 0b1111
    dup = None
    qos = None
    packet_id = None
    topic = None

    remaining_length, body_start = _decode_remaining_length(packet)
    body_end = body_start + remaining_length
    if body_end > len(packet):
        msg = "remaining length exceeds packet size"
        raise ValueError(msg)

    body = packet[body_start:body_end]

    match packet_type:
        case PacketType.PUBLISH:
            dup = (flags & 0b1000) != 0
            qos = (flags >> 1) & 0b11
            topic, cursor = _decode_topic(body)
            packet_id, cursor = _decode_packet_id(body, start=cursor) if qos > 0 else (None, cursor)
            payload = body[cursor:]
        case PacketType.SUBSCRIBE:
            qos = (flags >> 1) & 0b11
            topic, cursor = _decode_topic(body)
            payload = body[cursor:]
        case PacketType.PUBACK:
            packet_id, cursor = _decode_packet_id(body)
            payload = body[cursor:]
        case _:
            payload = body

    return Packet(
        type=packet_type,
        dup=dup,
        qos=qos,
        identifier=packet_id,
        topic=topic,
        payload=payload,
        src_addr=src_addr,
    )


class Client:
    """MQTT/UDP client."""

    def __init__(
        self,
        *,
        listen_addr: tuple[str, int] = ("", 1883),
        send_addr: tuple[str, int] = ("255.255.255.255", 1883),
        src_addr: tuple[str, int] = ("", 0),
        send_timeout: float | None = 1.0,
    ) -> None:
        """Create a new MQTT/UDP client."""
        self._send_addr = send_addr
        self._running = False

        self._tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._tx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._tx_socket.settimeout(send_timeout)
        self._tx_socket.bind(src_addr)

        self._rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._rx_socket.bind(listen_addr)

    def __enter__(self) -> Self:
        """Return a client for use in a context manager."""
        return self

    def __exit__(self, *_args: object) -> None:
        """Clean up client resources."""
        self.close()

    @overload
    def publish(
        self,
        topic: str,
        payload: bytes,
        /,
        *,
        qos: Literal[0] = 0,
    ) -> None: ...

    @overload
    def publish(
        self,
        topic: str,
        payload: bytes,
        /,
        *,
        qos: Literal[1],
        dup: bool = False,
        identifier: int,
    ) -> None: ...

    def publish(
        self,
        topic: str,
        payload: bytes,
        /,
        *,
        dup: bool = False,
        qos: int = 0,
        identifier: int | None = None,
    ) -> None:
        """Send an MQTT/UDP PUBLISH message."""
        flags = (dup << 3) | (qos << 1)
        packet_id_bytes = b"" if identifier is None else _encode_packet_id(identifier)
        packet = _encode_packet(
            PacketType.PUBLISH,
            flags=flags,
            body=_encode_topic(topic) + packet_id_bytes + payload,
        )
        self._tx_socket.sendto(packet, self._send_addr)

    def puback(self, identifier: int, /) -> None:
        """Send an MQTT/UDP PUBACK message."""
        packet = _encode_packet(PacketType.PUBACK, body=_encode_packet_id(identifier))
        self._tx_socket.sendto(packet, self._send_addr)

    def subscribe(self, topic: str, /, *, qos: Literal[0, 1, 2] = 0) -> None:
        """Send an MQTT/UDP SUBSCRIBE message."""
        flags = qos << 1
        packet = _encode_packet(PacketType.SUBSCRIBE, flags=flags, body=_encode_topic(topic))
        self._tx_socket.sendto(packet, self._send_addr)

    def pingreq(self) -> None:
        """Send an MQTT/UDP PINGREQ message."""
        packet = _encode_packet(PacketType.PINGREQ)
        self._tx_socket.sendto(packet, self._send_addr)

    def pingresp(self) -> None:
        """Send an MQTT/UDP PINGRESP message."""
        packet = _encode_packet(PacketType.PINGRESP)
        self._tx_socket.sendto(packet, self._send_addr)

    def listen(
        self,
        /,
        *,
        buffer_size: int = 65535,
    ) -> Iterator[Packet]:
        """Yield incoming packets."""
        self._running = True
        while self._running:
            try:
                raw_packet, src_addr = self._rx_socket.recvfrom(buffer_size)
            except OSError:
                if self._running:
                    raise
                break

            yield _decode_packet(raw_packet, src_addr=src_addr)

    def stop(self) -> None:
        """Stop the listen loop."""
        self._running = False

    def close(self) -> None:
        """Close the client sockets."""
        self.stop()
        self._tx_socket.close()
        self._rx_socket.close()
