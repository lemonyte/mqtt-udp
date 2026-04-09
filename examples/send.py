#!/usr/bin/env python3
"""Command-line tool for sending MQTT/UDP messages."""

import argparse

from mqtt_udp import Client, PacketType


def main() -> None:
    parser = argparse.ArgumentParser(description="Send an MQTT/UDP message.")
    parser.add_argument(
        "packet_type",
        choices=list(PacketType.__members__),
        help="type of MQTT/UDP packet to send",
    )
    parser.add_argument("topic", default=None, help="topic name", nargs="?")
    parser.add_argument("payload", default=None, help="message payload", nargs="?")
    parser.add_argument("--dup", action="store_true", help="set the DUP flag")
    parser.add_argument("--qos", type=int, choices=[0, 1, 2], default=0, help="QoS level")
    parser.add_argument("--identifier", type=int, default=None, help="packet identifier")
    args = parser.parse_args()

    with Client() as client:
        match PacketType[args.packet_type]:
            case PacketType.PUBLISH:
                if args.topic is None:
                    parser.error("topic is required for PUBLISH packets")
                payload = (args.payload or "").encode()
                if args.qos != 0:
                    if args.identifier is None:
                        parser.error("identifier is required for PUBLISH packets with QoS > 0")
                    client.publish(
                        args.topic,
                        payload,
                        qos=args.qos,
                        dup=args.dup,
                        identifier=args.identifier,
                    )
                else:
                    client.publish(args.topic, payload)
            case PacketType.PUBACK:
                if args.identifier is None:
                    parser.error("identifier is required for PUBACK packets")
                client.puback(args.identifier)
            case PacketType.SUBSCRIBE:
                if args.topic is None:
                    parser.error("topic is required for SUBSCRIBE packets")
                client.subscribe(args.topic, qos=args.qos)
            case PacketType.PINGREQ:
                client.pingreq()
            case PacketType.PINGRESP:
                client.pingresp()


if __name__ == "__main__":
    main()
