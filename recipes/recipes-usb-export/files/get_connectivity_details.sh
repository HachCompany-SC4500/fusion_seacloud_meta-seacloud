#!/bin/bash

# This script outputs some details about connectivity.
# It is used when exporting service logs but also by Eagle BE when collecting connectivity details

ifconfig
echo
echo "   _________________________"
echo
echo
ip route
echo
echo "   _________________________"
echo
echo
timedatectl show-timesync
