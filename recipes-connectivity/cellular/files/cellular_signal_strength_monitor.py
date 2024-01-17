#!/usr/bin/python3

#########################################################################
'''
The role of this script is to get Cellular signal_strength and notify it to the backend
'''
#########################################################################

import sys
import lib_modem
import backendBridgeSocketIO
import dbus
import time
import signal
import logging

# global variables for signal strength value log reduction
counter_send = 0
previous_signal_strength = -1
kill_now = False

# It sends signal_strength status to backend via socketIO
# Data sent is made of an signal_strength value and a status
def sendSignalStrengthStatusToBackend(signal_strength, enabled, tech):
	try:
		# Notify backend
		state = 'enabled' if enabled == True else 'disabled'
		status = {
			'cellular_signal_strength': signal_strength,
			'cellular_state': 'error' if signal_strength == -1 else state,
			'cellular_tech': tech
			}
		backendBridgeSocketIO.sendSystemStatusToBackend(status)
	except:
		logger.error("Error while sending Cellular signal_strength status ")

# It sends signal_strength status to backend when value has changed or at least every 5 minutes
def monitorSignalStrengthValue(signal_strength, tech):
	global counter_send, previous_signal_strength
	counter_send += 1

	send_to_be = True

	# send to backend if value has changed or at least every 5 minutes
	if previous_signal_strength != signal_strength:
		logger.info("Cellular signal_strength value changed: %d -> %d" % (previous_signal_strength, signal_strength))
		previous_signal_strength = signal_strength
	# print log at least every 5 minutes
	elif counter_send % 100 == 0:
		logger.info("Cellular signal_strength %d" % (signal_strength))
		counter_send = 0
	else:
		send_to_be = False

	if send_to_be:
		sendSignalStrengthStatusToBackend(signal_strength, True, tech)

#Infinite loop on signal strength (=signal_strength) reading
def pollCellularSignalStrength():
	error_count = 0
	while not kill_now:
		signal_strength = -1
		tech = 'none'
		modem_on_dbus, message = lib_modem.isModemOnDBus(bus)
		if modem_on_dbus:
			signal_strength, message, tech = lib_modem.getSignalStrength(bus)

		if signal_strength == -1:
			# due to an unknown issue it is possible that we receive inadvertent -1 values
			# we do not want to send to BEFE the -1 value yet, only if it repeats over 30sec (10 poll)
			error_count += 1
			logger.error("Error while getting Cellular signal_strength value from dbus")

		# if we reached 10 poll we want to send the value to BEFE
		# if the signal_strength differ from -1 we reset the error count
		if signal_strength != -1 or error_count >= 10:
			if signal_strength != -1:
				error_count = 0
			monitorSignalStrengthValue(signal_strength, tech)

		time.sleep(3)

	# end of polling loop, most probably because cellular has been disabled : notify backend
	logger.info("Cellular has been disabled")
	sendSignalStrengthStatusToBackend(0, False, tech)

# callback signaled when SIGINT or SIGTERM is received
# most probably because cellular has been disabled
def exitGracefully(self, signum):
	global kill_now
	kill_now = True

#main program
if __name__ == '__main__':

	# Redirect logging messages to stdout
	logger = logging.getLogger(__name__)
	logger.addHandler(logging.StreamHandler(sys.stdout))
	logger.setLevel(logging.INFO)

	logger.info("Start cellular signal_strength monitor")

	# set callback signaling end of execution
	signal.signal(signal.SIGINT, exitGracefully)
	signal.signal(signal.SIGTERM, exitGracefully)

	# Get DBus
	bus = dbus.SystemBus()

	# prefer polling mode in order to detect when modem is locked or removed etc
	pollCellularSignalStrength()

	logger.info("End of cellular signal_strength monitor")

	exit(0)
