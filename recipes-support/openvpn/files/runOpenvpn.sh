#!/bin/sh

# This script starts the OpenVPN client on startup of the Seacloud
# /etc/ovpn.cfg needed
# /etc/keys needed

# Defines
MKDIR=/bin/mkdir
MKNOD=/bin/mknod

OPENVPN=/usr/sbin/openvpn
OPENVPN_USER=%OPENVPN_USER%
OPENVPN_GROUP=%OPENVPN_GROUP%
OPENVPN_CONFIG=/etc/keys/openvpn.cfg

# check key file content for disable pattern, if found (e.g. on R&D devices) we don't start openvpn
HOSTNAME=`cat /etc/hostname`
FILENAME_KEY=/etc/keys/$HOSTNAME.key
DISABLE_PATTERN="invalid key on purpose for WQG"
PID_FILE="/var/run/openvpn.pid"

# Starting openvpn
start() {
	echo "starting openvpn"

	# Check for presence of certificates
	if [ ! -e "$FILENAME_KEY" ] || [ ! -e "$OPENVPN_CONFIG" ]; then
		echo "\"$FILENAME_KEY\" or \"$OPENVPN_CONFIG\" is missing."
		echo "Openvpn can't be started"
	elif grep -q "$DISABLE_PATTERN" $FILENAME_KEY; then
		# If the "Disable pattern" is present in the key file, that means the amqp.json is present but can't be used for VPN. 
		echo "openvpn disable pattern \"$DISABLE_PATTERN\" found in file $FILENAME_KEY"
		echo "Openvpn not started"

		# This is a kind of "success" and will stop restart mechanism done by systemd
		return 0
	else
		echo "start openvpn"

		# Start OpenVPN client that will receive network frame via tun device, encrypt the frame and forward them to OpenVPN server.
		$OPENVPN --config $OPENVPN_CONFIG --user $OPENVPN_USER --group $OPENVPN_GROUP --writepid $PID_FILE &

		return 0
	fi
	return 1
}

# Stopping openvpn
stop() {
	echo "stopping openvpn"
	# Get Process ID
	if [ -f $PID_FILE ]; then
		PID=$(cat $PID_FILE)
	else
		PID=$(pgrep openvpn)
		if [ $? -ne 0 ]; then
			echo "No openvpn process found"
			return -1
		fi
	fi
	# Kill openvpn process and wait it is killed
	kill $PID
	while kill -0 $PID &>/dev/null ; do
		usleep 200000
	done

	# Clean PID file
	rm -f $PID_FILE
	return 0    
}

# main
case "$1" in
	start)
		start
	;;
	stop)
		stop
	;;
	*)
		start
esac

exit $?
