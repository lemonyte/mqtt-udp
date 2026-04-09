#!/usr/bin/env python3
"""Bi-directional MQTT/UDP and MQTT broker gateway."""

from datetime import datetime

import paho.mqtt.client as mqtt

import mqtt_udp


def handle_message(_client: mqtt.Client, udp_client: mqtt_udp.Client, message: mqtt.MQTTMessage) -> None:
    print(f"[{datetime.now()}] Forwarding PUBLISH {message.topic} to MQTT/UDP")
    udp_client.publish(message.topic, message.payload)


try:
    with mqtt_udp.Client() as udp_client:
        broker_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata=udp_client)
        broker_client.on_message = handle_message
        broker_client.connect("localhost", 1883)
        # If you subscribe to "#", you will receive the messages forwarded from MQTT/UDP, causing an infinite loop.
        broker_client.subscribe("demo/broker/#")
        broker_client.loop_start()

        for packet in udp_client.listen():
            if packet.type is mqtt_udp.PacketType.PUBLISH and packet.topic is not None:
                print(f"[{datetime.now()}] Forwarding PUBLISH {packet.topic} to MQTT broker")
                broker_client.publish(packet.topic, packet.payload)
except KeyboardInterrupt:
    pass
finally:
    broker_client.disconnect()
    broker_client.loop_stop()
