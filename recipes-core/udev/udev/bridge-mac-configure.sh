#!/bin/sh
#
# Systemd does not provide a mechanism for MAC address inheritance.
# In the case of a bridge device it's possible to provide either
# a hardcoded address or allow it to be randomly generated based on machine-id.
# To avoid getting random MAC and IP addresses after every update,
# a common practice to reuse one of Ethernet MAC addresses has been taken.


bridge_dev="/sys/class/net/br0"
ethernet_dev="/sys/class/net/fec1"

if [ -d $bridge_dev ] && [ -d $ethernet_dev ]; then
    bridge_addr=`cat $bridge_dev/address`
    ethernet_addr=`cat $ethernet_dev/address`

    if [ "$bridge_addr" != "ethernet_addr" ]; then
        ip link set dev br0 address $ethernet_addr
    fi
fi
