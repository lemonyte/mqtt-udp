#!/usr/bin/env python3
"""MQTT/UDP QoS example."""

import random
import threading
import time
from contextlib import suppress
from datetime import datetime

from mqtt_udp import Client, PacketType

TOPIC = "demo/qos"
DATA = b"important message"

send_queue: dict[int, tuple[str, bytes]] = {}


def get_packet_identifier() -> int:
    while True:
        identifier = random.randint(1, 65535)
        if identifier not in send_queue:
            return identifier


def receiver(client: Client) -> None:
    for packet in client.listen():
        identifier = packet.identifier
        match packet.type:
            case PacketType.PUBLISH:
                qos = packet.qos
                dup = packet.dup
                print(f"[{datetime.now()}] <<< Received PUBLISH {packet.topic} {qos=} {dup=} {identifier=}")

                if qos == 1 and identifier is not None:
                    # Randomly drop some packets.
                    if random.randint(0, 3) != 0:
                        print(f"[{datetime.now()}] >>> Sending PUBACK {identifier=}")
                        client.puback(identifier)
                    else:
                        print(f"[{datetime.now()}] !!! Dropped PUBLISH {identifier=}")
            case PacketType.PUBACK:
                print(f"[{datetime.now()}] <<< Received PUBACK {identifier=}")
                if identifier is not None:
                    send_queue.pop(identifier)


with Client() as client, suppress(KeyboardInterrupt):
    receiver_thread = threading.Thread(target=receiver, args=(client,), daemon=True)
    receiver_thread.start()
    while True:
        identifier = get_packet_identifier()
        print(f"[{datetime.now()}] >>> Sending PUBLISH {TOPIC} {identifier=}")
        client.publish(TOPIC, DATA, qos=1, identifier=identifier)
        send_queue[identifier] = (TOPIC, DATA)

        time.sleep(3)
        print()

        # Resend unacknowledged messages.
        for identifier, (topic, payload) in send_queue.items():
            print(f"[{datetime.now()}] >>> Resending PUBLISH {topic} {identifier=}")
            client.publish(topic, payload, qos=1, dup=True, identifier=identifier)
