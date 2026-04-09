#!/usr/bin/env python3
"""Simple MQTT/UDP publisher example."""

import json
import random
import threading
import time
from contextlib import suppress
from datetime import datetime

from mqtt_udp import Client, PacketType, match_topic

TOPIC = "demo/temperature"


def get_temperature() -> bytes:
    return json.dumps(random.uniform(20.0, 30.0)).encode("utf-8")


def receiver(client: Client) -> None:
    for packet in client.listen():
        match packet.type:
            case PacketType.PINGREQ:
                print(f"[{datetime.now()}] <<< Received PINGREQ")
                print(f"[{datetime.now()}] >>> Sending PINGRESP")
                client.pingresp()
            case PacketType.SUBSCRIBE:
                print(f"[{datetime.now()}] <<< Received SUBSCRIBE {packet.topic}")
                if packet.topic is not None and match_topic(packet.topic, TOPIC):
                    print(f"[{datetime.now()}] >>> Responding with PUBLISH {TOPIC}")
                    # Ignoring requested QoS for simplicity.
                    client.publish(TOPIC, get_temperature())


with Client() as client, suppress(KeyboardInterrupt):
    receiver_thread = threading.Thread(target=receiver, args=(client,), daemon=True)
    receiver_thread.start()
    while True:
        print(f"[{datetime.now()}] >>> Sending PUBLISH {TOPIC}")
        client.publish(TOPIC, get_temperature())
        time.sleep(3)
