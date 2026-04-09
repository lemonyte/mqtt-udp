#!/usr/bin/env python3
"""MQTT/UDP packet listener example."""

from contextlib import suppress
from datetime import datetime

from mqtt_udp import Client

with Client() as client, suppress(KeyboardInterrupt):
    for packet in client.listen():
        qos = packet.qos
        dup = packet.dup
        identifier = packet.identifier
        src_addr = packet.src_addr
        print(
            (
                f"[{datetime.now()}] <<< {packet.type} {packet.topic}"
                f" {qos=} {dup=} {identifier=} {src_addr=}: {packet.payload!r}"
            ),
        )
