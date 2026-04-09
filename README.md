# mqtt-udp

A tiny, modern MQTT/UDP client.

> [!TIP]
> To learn how MQTT/UDP is different from traditional MQTT, read [this](https://mqtt-udp.readthedocs.io/en/stable/).

## Features

- Brokerless broadcasting of MQTT messages
- Fire-and-forget
- Reliable transmission support with QoS level 1
- Polling using `SUBSCRIBE` messages
- Ping messages for client discovery
- No dependencies and single-file distributable for easy vendoring and embedded systems

## Non-goals

MQTT/UDP is based on [MQTT v3.1.1](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html) but it does not aim to be 100% compatible.
The following are not implemented nor planned:

- `CONNECT`, `CONNACK`, `SUBACK`, `UNSUBSCRIBE`, `UNSUBACK`, `DISCONNECT`, and `AUTH` messages
- `PUBREC`, `PUBREL`, and `PUBCOMP` (QoS level 2)
- Packet Identifier in `SUBSCRIBE` messages
- Multiple topics in `SUBSCRIBE` messages
- Retained messages
- Authentication
- Message Properties

The following are not done automatically but can be easily implemented by the user:

- Replying to `PUBLISH` with `PUBACK` (QoS level 1)
- Replying to `PINGREQ` with `PINGRESP`
- Resending unacknowledged messages

## Usage

These are the most bare-bones examples to get you started.

Sending messages:

```python
from mqtt_udp import Client

with Client() as client:
    client.publish("demo/topic", b"hello")
```

Receiving messages:

```python
from mqtt_udp import Client

with Client() as client:
    for packet in client.listen():
        print(packet)
```

For more complete examples that you can use right away, check out the [examples](examples) directory.

## License

[MIT License](LICENSE)

## Credits

This implementation is based on [this desciption](https://mqtt-udp.readthedocs.io/en/stable/) of MQTT/UDP by [Dmitry Zavalishin](https://github.com/dzavalishin).
Many thanks to him for the idea and prior work!
