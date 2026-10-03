---
title: MQTT/UDP Protocol
icon: lucide/network
---

## A primer

MQTT/UDP, originally [described](https://mqtt-udp.readthedocs.io/en/stable/) by Dmitry Zavalishin, is a protocol based on MQTT v3.1.1 that uses UDP instead of TCP as the underlying transport protocol.

It is much simpler than MQTT, using only a subset of the MQTT Control packets and eliminating the need for a broker by broadcasting all packets.

This document attempts to explain how MQTT/UDP (as implemented by `mqtt-udp`) differs from MQTT, what it aims to do, and what it doesn't do.
It also serves as a set of guidelines for how clients using MQTT/UDP should behave.

!!! tip
    To best understand this specification, I recommend you first familiarize yourself with the [MQTT specification](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html) and refer back to it while reading about the differences.

Throughout this document, "client" refers to any device that sends or receives MQTT/UDP packets, "subscriber" refers to a client that is interested in receiving messages, and "publisher" refers to a client that is sending messages.
A client can be both a publisher and a subscriber simultaneously.

## Brokerless broadcasting

MQTT/UDP removes the need for a broker by broadcasting all packets to all clients in the network.
It is up to the client to filter out packets that are irrelevant based on the topic.

Clients *may* send packets directly to a specific IP address instead of broadcasting, if the IP address is known.
This is useful for `PUBACK` packets to avoid Packet Identifier collisions.

Clients *must* accept both broadcast packets and unicast packets sent directly to their IP address.

The default port for MQTT/UDP is `1883`, which may be used simultaneously with TCP-based MQTT.
A gateway for bridging MQTT/UDP and MQTT can be trivially implemented by forwarding packets between the two protocols.

## Reliable transmission

In cases where it is important that a `PUBLISH` packet is received by **at least one** subscriber, a publisher can set the QoS level to `1`.
The `PUBLISH` packet *must* then also include a random Packet Identifier that is unique to the publisher.
The publisher should make a note of outgoing `PUBLISH` packets and remove them upon receiving a `PUBACK` packet with the corresponding Packet Identifier.

When a client receives a `PUBLISH` packet with QoS level `1`, it *must* respond with a `PUBACK` packet containing the same Packet Identifier as the `PUBLISH` packet.

!!! warning
    Because the `PUBACK` packets are also broadcasted, it is possible that the Packet Identifier collides with that of another unrelated `PUBLISH` packet, causing a publisher to mark an unacknowledged `PUBLISH` packet as acknowledged.
    For this reason, it is recommended to always use a new random number between `0x0` and `0xFFFF` as the Packet Identifier to minimize the chances of a collision, and to send `PUBACK` packets directly to the publisher's IP address instead of broadcasting if possible.

If a `PUBACK` packet is not received, the publisher may retransmit the `PUBLISH` packet with the same Packet Identifier and the DUP flag set.
The publisher is free to choose the length of time to wait before retransmitting and the number of retransmissions.

QoS level `2` is not supported in MQTT/UDP.

## Polling

MQTT/UDP uses the `SUBSCRIBE` packet in a slightly different manner than MQTT.
Instead of sending a `SUBSCRIBE` packet to a broker, to which the broker responds with a `SUBACK` packet and starts sending matching `PUBLISH` packets, in MQTT/UDP the `SUBSCRIBE` packet is used to poll for messages from a publisher.
This is useful when you only want to send a message in response to a request, avoiding spamming the network with packets when no one is listening.

When a publisher receives a `SUBSCRIBE` packet, it *should* respond with a `PUBLISH` packet for each matching topic that the publisher has.

The QoS level of the `SUBSCRIBE` packet indicates the requested QoS level for the subsequent `PUBLISH` packets.
A publisher *must* set the QoS level of the `PUBLISH` packet to be equal to or lower than the requested QoS level.

`SUBSCRIBE` is the only packet in MQTT/UDP whose structure differs from the MQTT spec.
These differences are:

- There is no Packet Identifier
- There is only **one** topic filter in the payload, encoded after the fixed header
- Instead of being encoded after the topic filter, the requested QoS level is encoded in bits 2 and 1 of the fixed header

### Fixed header

<table>
    <thead>
        <tr>
            <th>Bit</th>
            <th>7</th>
            <th>6</th>
            <th>5</th>
            <th>4</th>
            <th>3</th>
            <th>2</th>
            <th>1</th>
            <th>0</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>byte 1</td>
            <td colspan="4">MQTT Control Packet type (8)</td>
            <td>Reserved</td>
            <td colspan="2">Requested QoS level</td>
            <td>Reserved</td>
        </tr>
        <tr>
            <td>byte 2...</td>
            <td colspan="8">Remaining length</td>
        </tr>
    </tbody>
</table>

### Payload format

<table>
    <thead>
        <tr>
            <th>Byte</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>byte 1</td>
            <td>Length MSB</td>
        </tr>
        <tr>
            <td>byte 2</td>
            <td>Length LSB</td>
        </tr>
        <tr>
            <td>byte 3...</td>
            <td>Topic filter</td>
        </tr>
    </tbody>
</table>

## Client discovery

If a client wishes to discover other clients in the network, it can send a `PINGREQ` packet.
When a client receives a `PINGREQ` packet, it *must* respond with a `PINGRESP` packet.

This is useful for checking if other clients exist in the network and determining their IP addresses.
