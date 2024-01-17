#!/usr/bin/python3

################################################################################################
'''
The role of this script is to get Wi-Fi RSSI and notify it to the backend
It also tries to reconnect if there is a registered service but the connection is not stablished
'''
################################################################################################

import lib_wifi
import lib_logger
import backendBridgeSocketIO
import logging
import signal
import lib_system
import threading
import glob
import os

GET_LOCK_TIMEOUT = 0 # Max seconds to wait to get the lock, when using timeout mode (0 means no timeout mode, try only once)
LOGS_FILE_PATH = "/media/persistent/system/wifi_rssi_monitor_logs"
LOGS_FILE_MAX_BYTES = 512*1024
LOGS_FILE_BACKUP_COUNT = 1

# Size of logs generated when connected: 4.7 KBytes
# Size of logs generated when not connected: 5.5 Kbytes
# The script is executed by the corresponding timer service, every 30 seconds
# 512 KBytes --> History of the last 93 runs (46 minutes) when not connected, or the last 108 runs (54 minutes) when connected

logger = logging.getLogger(__name__)
lock_acquired = False


def terminationSignalHandler(self, signal_number):
	logger.info("Termination signal received (SIGINT or SIGTERM)")
	try:
		if reconnection_thread is not None:
			services_list = glob.glob(lib_wifi.CONFIGURATION_FILES_PATH + "/wifi_*_managed_*")
			if services_list:
				# The list is not empty, abort reconnection process
				# Only one registered service is allowed, so the list should contain only one element
				connman_service = os.path.basename(services_list[0])
				logger.info("Aborting reconnection to {}".format(connman_service))
				lib_system.call_shell(["/bin/sh","-c", "connmanctl disconnect " + connman_service + " 2>/dev/null"])
			else:
				logger.warning("Expected WiFi configuration folder not found. Skip aborting reconnection")
	except Exception as e:
		logger.error("Exception while aborting reconnection: {}",format(e))

	if lock_acquired:
		wifi_manager.release_lock()
	exit(0)


def reconnect():
	# Extract ssid from global variable registered_service and reconnect
	if registered_service is not None:
		ssid, encoded_ssid  = registered_service
		wifi_manager.reconnect(ssid)


def get_connection_status():
	# Gets rssi, tech, and ip address from the wireless interface
	# TODO IP ADDRESS IS NOT VALID HERE, required to decode + strip and validate with from ipaddress import ip_address
	(error_code, ip_address) = lib_system.call_shell(["/bin/sh","-c", "ifconfig " + lib_wifi.WIFI_INTERFACE_NAME + " | egrep -o 'inet addr:[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | cut -d':' -f2"], False)
	if error_code:
		ip_address = None
	success, message, rssi, tech = wifi_manager.get_rssi()
	return (success, message, rssi, tech, ip_address)


if __name__ == '__main__':
	success = True
	reconnection_thread = None
	registered_service = None
	ip_address = None
	rssi = "error"
	tech = 0

	tag_name = "wifi_rssi_monitor"
	lib_logger.add_handler_file(tag_name, LOGS_FILE_PATH, LOGS_FILE_MAX_BYTES, LOGS_FILE_BACKUP_COUNT)
	lib_logger.log_header("Wi-Fi RSSI MONITOR START - Log time is in UTC")

	# Assign termination signal handlers
	signal.signal(signal.SIGINT, terminationSignalHandler)
	signal.signal(signal.SIGTERM, terminationSignalHandler)

	# Get Wi-Fi manager object
	wifi_manager = lib_wifi.WiFiManager(logger)

	# Acquire configuration lock
	lock_acquired = wifi_manager.acquire_lock(GET_LOCK_TIMEOUT)
	if lock_acquired:
		# Get RSSI only if Wi-Fi is still enabled and configured
		status, message =  wifi_manager.get_wifi_enabled_status()
		if status is "enabled":
			success, message, registered_service = wifi_manager.get_registered_service()
			if success and len(registered_service) is not 0:
				# Get RSSI and tech. Use a try/except so that notification is sent even in case of exception
				try:
					success, message, rssi, tech, ip_address = get_connection_status()
					if not success or not ip_address:
						# Try to reconnect and get rssi again.
						# reconnect function must be called from another thread so that, if requested, it can be aborted
						# from terminationSignalHandler via "connmanctl disconnect" when stopping wifi_rssi_monitor service.
						# Otherwise terminationSignalHandler is not executed until reconnect function ends, either when
						# connection succeeds, either when connection fails
						reconnection_thread = threading.Thread(target=reconnect, name="reconnect thread")
						reconnection_thread.daemon = True
						reconnection_thread.start()
						reconnection_thread.join()
						success, message, rssi, tech, ip_address = get_connection_status()
				except Exception:
					rssi = "error"
					tech = 0
					ip_address = None

				# Notify backend
				data = {
					'wifi_rssi': -1 if (rssi == 'error' or not ip_address) else int(rssi),
					'wifi_state': 'error' if (rssi == 'error' or not ip_address) else 'enabled',
					'wifi_tech': tech
					}
				backendBridgeSocketIO.sendSystemStatusToBackend(data)

		# Release configuration lock
		wifi_manager.release_lock()

	else:
		logger.info("Not able to get configuration lock. Nothing to do")


	# Return value
	if success:
		exit(0)
	exit(1)
