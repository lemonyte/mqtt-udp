#!/usr/bin/env python3
"""MQTT broker to MQTT/UDP gateway."""

from contextlib import suppress
from datetime import datetime

import paho.mqtt.client as mqtt

import mqtt_udp


def handle_message(_client: mqtt.Client, udp_client: mqtt_udp.Client, message: mqtt.MQTTMessage) -> None:
    print(f"[{datetime.now()}] Forwarding PUBLISH {message.topic} to MQTT/UDP")
    udp_client.publish(message.topic, message.payload)


with mqtt_udp.Client() as udp_client, suppress(KeyboardInterrupt):
    broker_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata=udp_client)
    broker_client.on_message = handle_message
    broker_client.connect("localhost", 1883)
    broker_client.subscribe("#")
    broker_client.loop_forever()
