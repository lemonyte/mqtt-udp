#!/usr/bin/env python3
"""MQTT/UDP to MQTT broker gateway."""

from contextlib import suppress
from datetime import datetime

import paho.mqtt.client as mqtt

import mqtt_udp

with mqtt_udp.Client() as udp_client, suppress(KeyboardInterrupt):
    broker_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    broker_client.connect("localhost", 1883)

    for packet in udp_client.listen():
        if packet.type is mqtt_udp.PacketType.PUBLISH and packet.topic is not None:
            print(f"[{datetime.now()}] Forwarding PUBLISH {packet.topic} to MQTT broker")
            broker_client.publish(packet.topic, packet.payload)
