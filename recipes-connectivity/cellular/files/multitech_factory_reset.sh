#!/bin/bash
#
# call like './multitech_factory_reset.sh [provider]'
#
# if no provider value passed, script will default to AT&T/Other
#
# Be aware: This is not really a factory reset, it resets only the
#           configuration for the provider- and usb-configuration.
#

function help() {
	echo "$( basename $0 ) <provider>"
	echo " Values for 'provider':"
	echo "    verizon"
	echo "    other"
}

function send_cmd() {
	echo -e -n "$1"'\r' > "${DEVICE}"
}

function setup_multitech() {
	local DEVICE="/dev/ttyACM3"
	local PROVIDER="${1:-other}"

	if [[ ! -e "$DEVICE" ]] ; then
		echo "Couldn't find modem '$DEVICE'" >&2
		exit 1
	fi

	echo "> Stopping interfering services"
	systemctl stop ofono
	systemctl stop connman
	systemctl stop cellular_data_supervisor.timer
	
	echo "> Setup serial port"
	stty -F ${DEVICE} 115200 raw -echo -echoe -echok -echoctl -echoke
	
	echo "> Setting Provider ($PROVIDER)"
	if [[ "$PROVIDER" == "verizon" ]] ; then
		send_cmd 'AT#FWSWITCH=1,1'
	else
		send_cmd 'AT#FWSWITCH=0,1'
	fi

	echo "> Waiting for modem restart"
	sleep 30

	echo "> Setting USB config"
	send_cmd 'AT#USBCFG=0'
	sleep 2
	send_cmd 'AT#REBOOT'
}

setup_multitech $*
