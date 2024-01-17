#!/bin/sh
# perform hard reboot on modem connected to external USB box
# it acts on pin "Enable" of chipset reponsible for power management of external USB box

echo 101 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio101/direction
echo 0 > /sys/class/gpio/gpio101/value

sleep 1

echo 1 > /sys/class/gpio/gpio101/value
echo 101 > /sys/class/gpio/unexport

sleep 10

exit 0
