#!/usr/bin/python3

import dbus
import lib_system
import os
import glob
import re
import subprocess
import ctypes
import logging
import lib_logger
from time import sleep
from shutil import rmtree
import fcntl
import fileinput
from collections import namedtuple
from gi.repository import GObject
from dbus.mainloop.glib import DBusGMainLoop
import threading
from enum import Enum

# We enable the DBus mainloop here to ensure it is enabled before connection
# to DBus is done, provided this library is imported at the very first start of
# the caller script.
# If a DBus connection has been made before enabling the mainloop, the mainloop
# is ineffective and any subbsequent asynchronous DBus calls will fail; for
# exemple, add_signal_receiver() is such a call that is used here.
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

CONFIGURATION_FILES_PATH = "/var/lib/connman"
CONNMAN_SETTINGS_FILE_PATH = CONFIGURATION_FILES_PATH + "/settings"
WPAS_DBUS_SERVICE = "fi.w1.wpa_supplicant1"
WPAS_DBUS_INTERFACE = "fi.w1.wpa_supplicant1"
WPAS_DBUS_OPATH = "/fi/w1/wpa_supplicant1"
WPAS_DBUS_INTERFACES_INTERFACE = "fi.w1.wpa_supplicant1.Interface"
WPAS_DBUS_BSS_INTERFACE = "fi.w1.wpa_supplicant1.BSS"
WIFI_INTERFACE_NAME = "wlan0"
LOCK_FILE_NAME = "/tmp/wifi_lock"
SIGNAL_SCAN_TIMEOUT_SEC = 15
SIGNAL_CONNECTION_TIMEOUT_SEC = 30
PSK_PASSPHRASE_LENGTH_MIN = 8
PSK_PASSPHRASE_LENGTH_MAX = 64


# all stuff containing information on USB dongles
USBDongleInfo = namedtuple("USBDongleInfo", "Name VidPid")

'''
List of all USB dongles supported by the system. Add here any further validated dongle.
'''
__supported_dongles = [
	USBDongleInfo("Realtek Semiconductor Corp RTL8811AU", "0bda:a811"),
]

'''
Enum Class with argument expansion type to be performed in function WiFiManager._execute_signal_based_function()
'''
class ArgumentExpansion(Enum):
	NO = 0
	TUPLE = 1
	DICTIONARY = 2

'''
Enum Class with connection error identifiers used in function WiFiManager.connect()
'''
class ConnectionError(Enum):
	NO = 0
	UNKNOWN = 1
	INVALID_KEY = 2
	AUTHENTICATION = 3


def byte_array_to_string(bytes):
	'''
	Converts array of bytes to string
	@bytes: array of bytes to convert
	Returns a string
	'''
	import urllib.parse
	string = ""
	for character in bytes:
		if character >= 32 and character < 127:
			string += "%c" % character
		else:
			string += urllib.parse.quote(chr(character))
	return string

def byte_array_to_hex_string(bytes):
	'''
	Converts array of bytes to hexadecimal string
	@bytes: array of bytes to convert
	Returns a string
	'''
	import urllib.parse
	string = ""
	for character in bytes:
		string += "%02X:" % character
	return string[0:-1]


def create_list(array_of_strings):
	'''
	Returns a list with the elements of an array of strings
	'''
	value = []
	for i in array_of_strings:
		value.append(str(i))
	return value


def encode_ssid(ssid):
	'''
	Returns encoded version of the ssid
	'''
	return ssid.encode('utf-8').hex()


def decode_ssid(encoded_ssid):
	'''
	Returns decoded version of the ssid
	'''
	return bytes.fromhex(encoded_ssid).decode('utf-8')


def get_properties_from_service_name(service):
	'''
	Returns properties extracted from service name (technology, mac, encoded_ssid, security)
	'''
	properties = service.split('_')
	technology = properties[0]
	mac = properties[1]
	encoded_ssid = properties[2]
	security = properties[4]
	return (technology, mac, encoded_ssid, security)


def get_properties_from_config_filename(config_filename):
	'''
	Returns properties extracted from the config filename (technology, mac, encoded_ssid)
	'''
	filename_no_extension = config_filename.split(".")[0]
	properties = filename_no_extension.split('_')
	technology = properties[0]
	mac = properties[1]
	encoded_ssid = properties[2]
	return (technology, mac, encoded_ssid)


def list_USB_dongles(logger):
	'''
	Return list of supported USB dongles currently mounted by the system.
	tuple (count, message, list)
	'''
	count = 0
	mounted_dongles = []
	message = "No dongle found"
	exception = False

	# We search dongles mounted by the system
	for supported_dongle in __supported_dongles:
		try:
			# check if this dongle exists in the system using lsusb command (searched by vendor Id & product Id)
			command = ['lsusb', '-d', supported_dongle.VidPid]
			with open(os.devnull, 'w') as shutup:
				subprocess.check_call(command, stdout=shutup, stderr=shutup)
			count += 1
			mounted_dongles.append(supported_dongle)
			message = "Dongle \'%s\' is detected" % (supported_dongle.Name)
		except subprocess.CalledProcessError as e:
			# this exception is raised when lusb commands failed to find a specific device
			# in this case we look for the next one
			pass
		except Exception as e:
			message = "Generic exception while getting USB dongle(s):%s" % (e)
			break

	if exception:
		logger.error(message)
	elif count > 1:
		message = "Several dongles are installed"
		logger.info(message)
	else:
		logger.info(message)

	return count, message, mounted_dongles


def get_section_from_connman_settings_file(file_name, section_name):
	'''
	Gets the list of items belonging to an specific section of a file.
	@file_name: full path of the file
	@section_name: string containing the name of the section to look for. E.g "WiFi"
	Returns a list of items on success, or an empty list on error

	The format of the file is expected to be:
	[section_name]
	item1
	item2
	itemN
	<empty line>

	Below and example of connman settings file:
	[global]
	OfflineMode=false

	[Wired]
	Enable=true
	Tethering=false

	[P2P]
	Enable=false
	Tethering=false

	[WiFi]
	Enable=true
	Tethering=false
	'''
	section_items_list = list()
	# Add surrounding square brackets [] to the section name to search only in section names
	section = "[" + section_name + "]"
	try:
		file = open(file_name, "r")
		section_found = False
		line = file.readline()
		while line and not section_found:
			line=line.strip()
			if section in line:
				# At this stage the requested section has been found
				# Continue reading lines from the file until finding the end of section (blank line)
				section_found = True
				end_of_section = False
				line=file.readline()
				while line and not end_of_section:
					line = line.strip()
					if not line:
						end_of_section = True
					else:
						section_items_list.append(line)
					line = file.readline()
			line = file.readline()
		file.close()
	except:
		if not file.closed():
			file.close()
		section_items_list.clear()

	return section_items_list


'''
Class WifiManager
Provides basic functions to manage wifi connection to an access point
'''
class WiFiManager(object):

	def __init__(self,logger):
		self.logger = logger
		self.interface_object = None		# To get access to the WiFi interface through wpa_supplicant (fi.w1.wpa_supplicant1.Interface)
		self.wpa_interface = None		# Path to access to WPA supplicant interface
		self.bus = dbus.SystemBus()		# The system DBus
		self.technology = None			# DBus Interface to WiFi technology via connman
		self.manager = None			# DBus Interface to connman
		self.connman_bound_to_wifi = False	# True if all DBus Interfaces to communicate with connman are correctly initialized, otherwise False
		self.lock_file = None			# File object to implement file lock mechanism
		self.loop = GObject.MainLoop()		# Main event loop needed to handle dbus signals
		self.signal_received = False		# Bool to indicate that the expected signal has been received
		self.event_loop_thread = None		# The thread to run gobject main loop
		self.stop_event_loop_thread = False	# Flag to indicate that event_loop_thread must exit
		self.scan_done_success = 0		# To signal result of a scan (1 success, 0 otherwise)
		self.service_security = "none" 		# String that indicates the security type of the service we want to connect to (none, psk, wps, ieee8021x)
		self.service_auth_errors = 0		# Authentication errors counter
		self._bind_connman_to_wifi()
		self.enabled_status, dummy_message = self.get_wifi_enabled_status()
		if self.enabled_status == "enabled":
			self._get_interface()
			self._get_interface_object()


	def _bind_connman_to_wifi(self):
		'''
		Bind connman to wifi, by updating self.bus, self.technology, and self.manager
		'''
		if self.connman_bound_to_wifi:
			return
		try:
			self.technology = dbus.Interface(self.bus.get_object("net.connman", "/net/connman/technology/wifi"), "net.connman.Technology")
			self.manager = dbus.Interface(self.bus.get_object('net.connman', '/'), 'net.connman.Manager')
			self.connman_bound_to_wifi = True
		except dbus.DBusException as e:
			self.logger.error("DBus exception while connman is binding to interface to interface %s: %s" % (WIFI_INTERFACE_NAME, e))
			self.technology = None
			self.manager = None
		except Exception as e:
			self.logger.error("Generic exception while connman is binding to interface to interface %s: %s" % (WIFI_INTERFACE_NAME, e))
			self.technology = None
			self.manager = None


	def _get_interface(self):
		'''
		Updates self.wpa_interface with the path to access to WPA supplicant interface
		'''
		if self.wpa_interface is not None:
			return
		try:
			wpa_supplicant_obj = self.bus.get_object(WPAS_DBUS_SERVICE, WPAS_DBUS_OPATH)
			wpa_supplicant = dbus.Interface(wpa_supplicant_obj, WPAS_DBUS_INTERFACE)
			path = wpa_supplicant.GetInterface(WIFI_INTERFACE_NAME)
			if_obj = self.bus.get_object(WPAS_DBUS_SERVICE, path)
			self.wpa_interface = dbus.Interface(if_obj, WPAS_DBUS_INTERFACES_INTERFACE)
		except dbus.DBusException as e:
			self.logger.error("DBus exception while wpa_supplicant is binding to interface %s: %s" % (WIFI_INTERFACE_NAME, e))
			self.wpa_interface = None
		except Exception as e:
			self.logger.error("Generic exception while wpa_supplicant is binding to interface %s: %s" % (WIFI_INTERFACE_NAME, e))
			self.wpa_interface = None


	def _get_interface_object(self, force = False, log_enabled = True):
		'''
		Updates self.interface_object with the path to the wifi interface object, if actual value is None
		@force: when True, the self.interface_object is updated even if it is not None.
			This is needed because if WiFi is disabled and enabled again (for instance, from config_wifi.py)
			the path to the interface object changes
		@log_enabled: if True the function will log, otherwise not.
		              This feature has been added to avoid logs every 3 seconds when the function is called from monitor_system.py
		'''
		if (self.interface_object is not None) and (force == False):
			return
		try:
			wpas_obj = self.bus.get_object(WPAS_DBUS_SERVICE, WPAS_DBUS_OPATH)
			wpas = dbus.Interface(wpas_obj, WPAS_DBUS_SERVICE)
			path = wpas.GetInterface(WIFI_INTERFACE_NAME)
			if log_enabled:
				self.logger.info("Path to Wi-Fi interface %s: %s" % (WIFI_INTERFACE_NAME, path))
			self.interface_object = self.bus.get_object(WPAS_DBUS_SERVICE, path)
		except dbus.DBusException as e:
			if log_enabled:
				self.logger.error("DBus exception while getting interface object of %s: %s" % (WIFI_INTERFACE_NAME, e))
			self.interface_object = None
		except Exception as e:
			if log_enabled:
				self.logger.error("Generic exception while getting interface object of %s: %s" % (WIFI_INTERFACE_NAME, e))
			self.interface_object = None


	def _get_interface_properties(self, log_enabled = True):
		'''
		Get the properties of the WiFi interface
		@log_enabled: if True the function will log, otherwise not.
		              This feature has been added to avoid logs every 3 seconds when the function is called from monitor_system.py
		Returns the properties
		'''
		self._get_interface_object(False, log_enabled)	# Ensure interface object exists
		attempts = 0
		properties = []
		while (attempts < 2):
			message = ""
			try:
				if (attempts != 0):
					if log_enabled:
						self.logger.error("Retry to get interface properties. Attempt #%s" % (attempts+1))
					self._get_interface_object(True, log_enabled)
				if self.interface_object is not None:
					properties = self.interface_object.GetAll(WPAS_DBUS_INTERFACES_INTERFACE, dbus_interface=dbus.PROPERTIES_IFACE)
					break;	# Exit while as we have been able to get interface properties (no exception produced)
			except dbus.DBusException as e:
				message = "DBus exception while getting interface properties: %s" % (e)
			except Exception as e:
				message = "Generic exception while getting interface properties: %s" % (e)
			finally:
				attempts = attempts +1

		if ((message != "") and (log_enabled)):
			self.logger.error(message)

		return properties


	def _run_event_loop(self):
		'''
		Starts the event loop used to catch dbus signals
		'''
		self.stop_event_loop_thread = False
		self.loop.run()
		while not self.stop_event_loop_thread:
			pass


	def _quit_event_loop(self):
		'''
		Quits the event loop used to catch dbus signals
		'''
		self.loop.quit()
		self.stop_event_loop_thread = True


	def _execute_signal_based_function(self, function, arguments, argument_expansion, timeout_sec, interface, signal_name, signal_handler):
		'''
		Executes a function, waits for the expected signal, and updates self.signal_received accordingly
		@function: the function to execute
		@arguments: a tuple containing the arguments of the function to execute
			Important note:
				If only one argument is required pass a tupple with a single element as shwon (single_argument,)
		@timeout_sec: timeout value, in seconds, to wait for the signal
			Important note:
				Don't set timeout to 0 as, in this case, the function won't return until the expected signal is received
				So, if the signal is never received, the function will never return!!!
		@interface: dbus interface that generates the signal
		@signal_name: the name of the signal
		@signal_handler: the function to handle the signal
		'''
		# Add receiver for signal_name
		self.bus.add_signal_receiver(signal_handler, dbus_interface=interface, signal_name=signal_name)

		# Run the event loop to enable signal handling, in a separate thread
		self.event_loop_thread = threading.Thread(target=self._run_event_loop, name="event_loop_thread")
		self.event_loop_thread.daemon = True
		self.event_loop_thread.start()

		# Launch the function (expand the arguments according to function definition)
		self.signal_received = False
		if (argument_expansion == ArgumentExpansion.TUPLE):
			function(*arguments)
		elif (argument_expansion == ArgumentExpansion.DICTIONARY):
			function(**arguments)
		else:
			function(arguments)

		# Join the event loop thread, with a timeout, to wait for the signal
		# When the expected signal is received, the event loop is finished and the thread ends
		self.event_loop_thread.join(timeout_sec)

		# At this stage, either the signal has been received (self.signal_received=True), either a timeout has occurred
		# If a timeout has occured, the thread will be automatically killed when exiting the script, as it's a daemon thread
		# Remove signal receiver
		self.bus.remove_signal_receiver(signal_handler, interface, signal_name)


	def _signal_scan_done(self,success):
		'''
		Handler function for "ScanDone" signal
		Updates self.scan_done_succes value, quits event loop, and sets self.signal_received = True to indicate expected singal received
		@success: result of the scan (1 succeeded, 0 otherwise)
		'''
		self.logger.info("Signal ScanDone received")
		self.scan_done_success = success
		self.signal_received = True
		self._quit_event_loop()


	def _signal_properties_changed(self, properties):
		'''
		Handler for "PropertiesChanged" signal. This signal is used to monitor connection progress
		Sends notifications to BE according to the criteria below:
			WPA enterprise networks:
				During authentication phase (State=associated), as it can take time
			Others:
				On first authentication error (WPA2-PSK), as second auth attempt can take time
				On authentication success (State=completed). This is, during network setup (get ip adres, etc.), as it can take time
		Quits the event loop when authentication succeeds(State=completed)
		@properties: the properties :-)
		'''

		if not "State" in properties:
			return

		self.logger.info("Signal PropertiesChanged received. State = {}".format(properties["State"]))

		# WPA enterprise, check if authentication has started and notify BE
		if "associated" in properties["State"] and "ieee8021x" in self.service_security:
			# Authentication started. Set error flag to True
			# The authentication error flag will be set to False if "completed" is received
			self.logger.info("WiFi service State=associated. 802.1x RSN authentication in progress")
			self.service_auth_errors += 1
			# Print connection state to stdout, so that BE is aware of it
			print("wifi_conn_state:auth_in_progress")
			return;

		# Check if authentication suceeded
		if "completed" in properties["State"]:
			# Print connection state to stdout, so that BE is aware of it
			if not "ieee8021x" in self.service_security:
				print("wifi_conn_state:getting_IP")
			self.logger.info("WiFi service State=completed. Getting IP address")
			self.service_auth_errors = 0
			self.signal_received = True
			self._quit_event_loop()
			return;

		# Authentication error handling for non enterprise networks (WPA2-PSK)
		if "4way_handshake" in properties["State"]:
			# Authentication started. Set error flag to True
			# The authentication error flag will be set to False if "completed" is received
			self.service_auth_errors += 1
			return;
		if ("disconnected" in properties["State"] and self.service_auth_errors > 0):
			self.logger.warning("WiFi service State=disconnected after 4way_handshake. Authentication attempt #{} failed".format(self.service_auth_errors))
			# Print connection state to stdout, so that BE is aware of it
			if self.service_auth_errors == 1:
				print("wifi_conn_state:auth_failed_retrying")
			return;


	def _scan_wifi(self):
		'''
		Launches a scan on wifi technology
		Returns a tupple (success, message)
		'''
		self.logger.info("Scanning Wi-Fi...")
		success = False
		message = "Scanning error"
		try:
			self._get_interface()	# Ensure that self.wpa_interface exists
			# Scan needs as parameters a dictionary with arguments describing scan type
			self._execute_signal_based_function(self.wpa_interface.Scan, ({'Type':'active'}), ArgumentExpansion.NO, timeout_sec=SIGNAL_SCAN_TIMEOUT_SEC, interface=WPAS_DBUS_INTERFACES_INTERFACE, signal_name="ScanDone", signal_handler=self._signal_scan_done)
			if self.signal_received and self.scan_done_success:
				success = True
				message = "Scanning complete"
			elif not self.signal_received:
				self._quit_event_loop()
				success = False
				message = "Scanning error. Timeout"
		except dbus.DBusException as e:
			self._quit_event_loop()
			message = "DBus exception while scanning Wi-Fi services on DBus: %s" % (e)
		except Exception as e:
			self._quit_event_loop()
			message = "Generic exception while scanning Wi-Fi services: %s" % (e)

		if success:
			self.logger.info(message)
		else:
			self.logger.error(message)

		self.event_loop_thread.join(1)
		return (success, message)


	def _find_service(self, ssid):
		'''
		Find a specific service
		@ssid: ssid of the service to find
		Returns a tupple (success, message, path, properties), where:
			success: True or False
			message: information message
			path: path of the service, if found, None otherwise
			properties: properties of the service, if found, None otherwise
		'''
		self.logger.info("Searching service %s..." % (ssid))
		success = False
		path = None
		service_properties = None
		message = "Service %s not found" % (ssid)
		self._bind_connman_to_wifi()	# Ensure connman is bound to wifi
		try:
			for path, properties in self.manager.GetServices():
				if "Name" in properties and properties["Name"] == ssid:
					message = "Service %s found at path: %s" % (ssid, path)
					service_properties = properties
					success = True
					break
		except dbus.DBusException as e:
			message = "DBus exception while searching Wi-Fi service on DBus: %s" % (e)
		except Exception as e:
			message = "Generic exception while searching Wi-Fi service: %s" % (e)

		if success:
			self.logger.info(message)
			lib_logger.log_header("Properties of service %s" % (ssid))
			self.logger.info(service_properties)
		else:
			self.logger.error(message)

		return (success, message, path, service_properties)


	def _acquire_lock(self, blocking = True):
		'''
		Tries to acquire a lock based on file lock mechanism
		@blocking: if True the function doesn't return until the lock is acquired
		Returns True on success, otherwise False
		'''
		self.lock_file = open(LOCK_FILE_NAME,"w")
		try:
			if blocking:
				fcntl.flock(self.lock_file,fcntl.LOCK_EX)
			else:
				fcntl.flock(self.lock_file,fcntl.LOCK_EX | fcntl.LOCK_NB)
		except IOError:
			return False
		return True


	def get_wifi_enabled_status(self, log_enabled = True):
		'''
		Gets the current status of wifi
		@log_enabled: if True the function will log, otherwise not.
		              This feature has been added to avoid logs every 3 seconds when the function is called from monitor_system.py
		Returns enabled, disabled or error
		'''
		if log_enabled:
			self.logger.info("Getting Wi-Fi status...")
		# By default, consider Wi-Fi is disabled
		status = "disabled"
		message = "Wi-Fi is disabled"
		success = True
		if os.path.isfile(CONNMAN_SETTINGS_FILE_PATH):
			# Consider Wi-Fi is enabled only if "Enable=true" is found in the [WiFi] section
			# If no [WiFi] section is found, consider also Wi-Fi is disabled
			if log_enabled:
				self.logger.info("Parsing file %s " % CONNMAN_SETTINGS_FILE_PATH)
			wifi_section = get_section_from_connman_settings_file(CONNMAN_SETTINGS_FILE_PATH,"WiFi")
			for item in wifi_section:
				if "Enable=true" in item:
					status = "enabled"
					message = "Wi-Fi is enabled"
					success = True
		else:
			status = "error"
			message = "File " + CONNMAN_SETTINGS_FILE_PATH + " doesn't exist"
			success = False

		if success:
			if log_enabled:
				self.logger.info(message)
		else:
			if log_enabled:
				self.logger.error(message)

		return (status, message)


	def disable_wifi_via_config_file(self, log_enabled = True):
		'''
		Disables wifi by writing directly to the configuration file.
		It must be used only to disable wifi when the USB dongle is not connected.
		The normal way to disable/enable Wifi is using "enable_wifi()"
		@log_enabled: if True the function will log, otherwise not.
		              This feature has been added to avoid logs every 3 seconds when the function is called from monitor_system.py
		Returns a tupple (success, message), where:
			success: True or False
			message: information message
		'''

		message = "Unable to disable WiFi via config file %s" % CONNMAN_SETTINGS_FILE_PATH
		success = False
		wifi_section = False
		any_wifi_section = False

		for line in fileinput.input(CONNMAN_SETTINGS_FILE_PATH, inplace=True):
			line.replace(" ","")	# Remove white spaces to prevent this script from failing in case the configuration file was manually changed before

			if "[WiFi]" in line:
				wifi_section = True
				any_wifi_section = True
			elif "[" in line:
				wifi_section = False
			if (wifi_section == True) and ("Enable=true" in line):
				line = "Enable=false"
				message = "Successfully disabled WiFi via config file %s" % CONNMAN_SETTINGS_FILE_PATH
				success = True
			if (wifi_section == True) and ("Enable=false" in line):
				message = "WiFi already disabled in config file %s" % CONNMAN_SETTINGS_FILE_PATH
				success = True

			# Required to populate the file (previously emptied by fileinput with inplace option) with updated values
			print ("%s" % line.rstrip("\r\n"))

		# If no [WiFi] section was found, consider also Wi-Fi is disabled
		if not any_wifi_section:
			success = True

		# Rename FIRST folder wifi_xxx --> _wifi_xxx_, and then FILE wifi_xxx --> _wifi_xxx_
		# The goals are:
		#   1 Automatic recovery of the connection as it happens after a normal Wi-Fi "disable"/"enable"
		#     "enable_wifi()" will restore the names by removing '_', if they are present
		#   2 Avoid Wi-Fi connection after "force disable"
		#     Even if we set "[WiFi] Enable=false" in "/var/lib/connman/settings", if we the user plugs the dongle again,
		#     connman will automatically connect to Wi-Fi, as it sees the configuration files. So, we need to rename them
		#     We rename instead of deleting them because we want to recovery the connection if Wi-Fi is enabled again (goal #1)
		if success and any_wifi_section:
			directory_name = CONFIGURATION_FILES_PATH + "/wifi_*"
			paths = glob.glob(directory_name)
			for name in paths:
				if not ".config" in name:
					os.rename(name, CONFIGURATION_FILES_PATH + "/_" + os.path.basename(name) + "_")
			for name in paths:
				if ".config" in name:
					os.rename(name, CONFIGURATION_FILES_PATH + "/_" + os.path.basename(name) + "_")

		if success:
			if log_enabled:
				self.logger.info(message)
		else:
			if log_enabled:
				self.logger.error(message)

		return (success, message)


	def verify_initialization(self):
		'''
		Returns the value of self.enabled_status
		'''
		if (self.enabled_status == "error"):
			return False
		if (self.enabled_status == "disabled"):
			return True
		if (self.connman_bound_to_wifi == False) or (self.wpa_interface == None):
			return False
		return True


	def enable_wifi(self, enable = True):
		'''
		Enables or disables wifi
		@enable: True to enable wifi, False to disable wifi
		Returns a tupple (success, message)
		'''

		self.logger.info("%s Wi-Fi..." % ("Enabling" if enable is True else "Disabling"))
		success = False
		self._bind_connman_to_wifi()	# Ensure connman is bound to wifi

		try:
			self.technology.SetProperty("Powered", enable)
			message = "Wi-Fi %s" % ("enabled" if enable is True else "disabled")
			self.enabled_status = "enabled" if enable else "disabled"
			success = True
		except dbus.DBusException as e:
			message = "DBus exception while %s Wi-Fi : %s" % ("enabling" if enable is True else "disabling", e)
		except Exception as e:
			message = "Generic exception while %s Wi-Fi %s" % ("enabling" if enable is True else "disabling", e)

		if (success and enable) or ("Already enabled" in message):
			# Rename FIRST FOLDER _wifi_xxx_ --> wifi_xxx, and then FILE _wifi_xxx_ --> wifi_xxx
			# Renaming is performed after successfully enable operation, or after exception due to Wi-Fi already enabled
			directory_name = CONFIGURATION_FILES_PATH + "/_wifi_*"
			paths = glob.glob(directory_name)
			for name in paths:
				if not ".config" in name:
					os.rename(name, CONFIGURATION_FILES_PATH + "/" + os.path.basename(name)[1:-1])
			for name in paths:
				if ".config" in name:
					os.rename(name, CONFIGURATION_FILES_PATH + "/" + os.path.basename(name)[1:-1])

		if success:
			self.logger.info(message)
		else:
			self.logger.error(message)

		return (success, message)


	def get_wifi_services(self, get_hidden = True, scan_wifi = True):
		'''
		Gets the list of available wifi services
		@get_hidden: If True, lists also the hidden APs
		Returns a tupple (success, message, wifi_services), where:
			wifi_services: list of services, made of [ name, [ security ], secure, connected, signal strength ], where:
				name: string
				security: list of supported security protocols
				secure: bool. True for secure APs (WPA2), False otherwise
				connected: bool
				signal strength: integer
		'''
		self.logger.info("Searching Wi-Fi services...")
		wifi_services = list()

		success = True
		if scan_wifi:
			success, message = self._scan_wifi()

		if success:
			try:
				# Create a dictionary that contains one entry for each secure APs found
				# The key is the ssid of the AP. The value doesn't matter, it is set to True
				secure_ssids_dict = {}

				# Create a dictionary to store the signal strength level in dBm, for each SSID found
				# The key is the ssid of the AP. The value is the RSSI in dBm
				signal_strength_dBm_dict = {}

				self._get_interface()	# Ensure that self.wpa_interface exists
				services_wpa_supplicant = self.wpa_interface.Get(WPAS_DBUS_INTERFACES_INTERFACE,'BSSs', dbus_interface=dbus.PROPERTIES_IFACE)
				self._bind_connman_to_wifi()	# Ensure connman is bound to wifi
				# Get RSN information element (rsnie) and signal strength in dBm from wpa_supplicant
				for opath in services_wpa_supplicant:
					try:
						net_obj = self.bus.get_object(WPAS_DBUS_SERVICE, opath)
						# Useful info. To get all properties of the scanned BSS you can use:
						# properties = net_obj.GetAll(WPAS_DBUS_BSS_INTERFACE,dbus_interface=dbus.PROPERTIES_IFACE)
						# print(properties)
						ssid = net_obj.Get(WPAS_DBUS_BSS_INTERFACE, 'SSID',dbus_interface=dbus.PROPERTIES_IFACE)
						ssid = byte_array_to_string(ssid)
						self.logger.info("SSID: %s" % ssid)
						bssid = net_obj.Get(WPAS_DBUS_BSS_INTERFACE, 'BSSID',dbus_interface=dbus.PROPERTIES_IFACE)
						bssid = byte_array_to_hex_string(bssid)
						self.logger.info("BSSID: %s" % bssid)
						signal_strength_dBm = net_obj.Get(WPAS_DBUS_BSS_INTERFACE, 'Signal',dbus_interface=dbus.PROPERTIES_IFACE)
						# Keep highest signal strength in case several AP broadcast the same SSID
						if ssid not in signal_strength_dBm_dict:
							signal_strength_dBm_dict[ssid] = signal_strength_dBm
						else:
							if (signal_strength_dBm > signal_strength_dBm_dict[ssid]):
								signal_strength_dBm_dict[ssid] = signal_strength_dBm
						# Warning: Some network where field "pairwise cipher suites count" is 0 are rejected by wpa_supplicant.
						# As a result, RSN property is missing and it generates an exception
						rsnie = net_obj.Get(WPAS_DBUS_BSS_INTERFACE, 'RSN',dbus_interface=dbus.PROPERTIES_IFACE)
						if len(rsnie["KeyMgmt"]) > 0:
							secure_ssids_dict[ssid] = True
					except Exception as e:
						self.logger.exception("Unexpected error during the parsing of wpa-supplicant network properties. Network skipped : considered unsecured and rely on signal strength provided by connman.")

				# Get and extract information of wifi services
				services = self.manager.GetServices()
				connected_service_properties = None
				connected_service_name = None
				for path, properties in services:
					if ( properties["Type"] != "wifi" ) or ( "Name" not in properties and not get_hidden ):
						continue
					wifi_name = properties["Name"] if "Name" in properties else ""
					security = create_list(properties["Security"])
					# Use the signal strength value obtained from wpa_supplicant
					# If it is not available, use the value obtained from connman - 120
					if wifi_name in signal_strength_dBm_dict:
						strength = int(signal_strength_dBm_dict[wifi_name])
					else:
						strength = int(properties["Strength"])-120
					connected = True if ("ready" or "online") in properties["State"] else False
					secure = True if wifi_name in secure_ssids_dict else False
					service = [wifi_name, security, secure, connected, strength]
					wifi_services.append(service)
					if connected:
						connected_service_name = wifi_name
						connected_service_properties = properties

				message = "Wi-Fi available network list: %s" % (wifi_services)
			except dbus.DBusException as e:
				message = "DBus exception while searching Wi-Fi services: %s" % (e)
				success = False
			except Exception as e:
				message = "Generic exception while searching Wi-Fi services: %s" % (e)
				success = False

			if success:
				lib_logger.log_header("Available Wi-Fi services")
				self.logger.info(wifi_services)
				if connected_service_properties is not None and connected_service_name is not None:
					lib_logger.log_header("Connected to %s" % (connected_service_name))
					self.logger.info("Properties: %s" % (connected_service_properties))
			else:
				self.logger.error(message)

		return (success, message, wifi_services)


	def get_current_connected_service(self, get_hidden = True, scan_wifi = True):
		'''
		Gets the current connected wifi service
		@get_hidden: If True, takes into accout also the hidden APs
		Returns a tupple (success, message, connected_service), where:
			connected service: list of connected services, made of [ name, [ security ], secure, connected, signal strength ], where:
			name: string
			security: list of supported security protocols
			secure: bool. True for secure APs (WPA2), False otherwise
			connected: bool
			signal strength: integer
		'''

		self.logger.info("Searching current connected service...")
		connected_service = []
		success, message, wifi_services = self.get_wifi_services(get_hidden, scan_wifi)

		if success:
			message = "No connected service found"
			for service in wifi_services:
				if service[3]:	 # service[3] contains connected status (True/False) of the sevice
					connected_service = service
					message = "Current connected service is: %s" % (connected_service)
					break

		if success:
			self.logger.info(message)
		else:
			self.logger.error(message)

		return (success, message, connected_service)


	def get_security_type(self, ssid):
		'''
		Gets the security type of an AP
		@ssid: ssid of the service to extract security type
		Returns a tupple (success,message, security_type), where:
			security_type: list made of supported security protocols
		'''
		self.logger.info("Getting security type of %s..." % (ssid))
		security_type = list()
		# Get the wifi service
		success, message, path, properties = self._find_service(ssid)
		if (success and path is not None):
			security_type= create_list(properties["Security"])
			message = "Security type of %s is %s" % (ssid, security_type)
			self.logger.info(message)

		return (success, message, security_type)


	def get_rssi(self):
		'''
		Gets the Received Signal Strength Indicator (dBm)
		Returns a tupple (success, message, rssi, tech), where:
			success: False in case of error, True otherwise
			message: last reported message
			rssi: RSSI value
			tech: the frequency of the used band. e.g.: 5200(5GHz band), 2437(2.4GHz band)
		'''
		rssi = "error"
		success = False
		message = "Error when trying to get signal strength"
		tech = "0"

		(error_code, output) = lib_system.call_shell(["/bin/sh","-c", "iw dev wlan0 link | grep -e signal -e freq"], False)
		if error_code is 0:
			info = output.decode('utf-8')
			info = info.replace('\n',';')

			match = re.search('freq: ([0-9]*);', info)
			if match is not None:
				tech = match.group(1)
				self.logger.info("FREQ = {} KHz".format(tech))
				success = True
			else:
				success = False

			match = re.search('signal: (-[0-9]*) dBm;*', info)
			if match is not None:
				rssi = match.group(1)
				self.logger.info("RSSI = {} dBm".format(rssi))
				success = True
			else:
				success = False
		if not success:
			self.logger.error(message)

		return (success, message, rssi, tech)


	def connect(self, ssid, security_params_dict, unregister = True):
		'''
		Connects to a service
		@ssid: ssid of the service to connect to
		@security_params_dict: a dictionary containing the keys and values of the needed security parameters
		Returns a tupple (success, message, error_code), where error_code is of type class ConnectionError(Enum)
		'''
		self.logger.info("Connecting to %s..." % (ssid))
		configuration_file = None
		error_code = ConnectionError.UNKNOWN

		# Get the wifi service. If first attempt fails, launch a scan and try a second one
		success, message, path, properties = self._find_service(ssid)
		if (path is None or not success):
			success, message = self._scan_wifi()
			if not success:
				return (success, message, error_code)
			success, message, path, properties = self._find_service(ssid)
			if (path is None or not success):
				return (success, message, error_code)

		try:
			success = False
			service_name = path.split("/")[-1]	# Get the last element [-1]
			(service_technology, service_mac, service_hexssid, self.service_security) = get_properties_from_service_name(service_name)
			configuration_file_path = CONFIGURATION_FILES_PATH + "/" + service_technology + "_" + service_mac + "_" + service_hexssid + ".config"

			# Disconnect, if already connected, otherwise an error is produced
			# Set AutoConnect property to false before disconnecting, otherwise it's not possible
			# to connect to a service with this scenario:
			# 	Connect to the service with the right password --> Succeeds
			#	Try to connect to the service with the wrong password --> Fails
			#	Try to connect to the service again with the right password --> Fails with "In progress error"
			services = self.manager.GetServices()
			for service_path, properties in services:
				if ( properties["Type"] != "wifi" ):
					continue
				if ("ready" or "online") in properties["State"]:	# Connected to this service
					wifi_name = properties["Name"] if "Name" in properties else ""
					self.logger.info("Connected to %s. Disconnect before creating configuration file" % (wifi_name))
					service = dbus.Interface(self.bus.get_object("net.connman", service_path), "net.connman.Service")
					service.SetProperty("AutoConnect", False)
					service.Disconnect()

			# Remove previous configuration file if it exists
			if os.path.isfile(configuration_file_path):
				os.remove(configuration_file_path)
				lib_system.sync()

			# Remove all registered wifi services, if any
			if unregister:
				success, message = self.remove_all()
				if not success:
					return (success, message, error_code)

			# Create the configuration file.
			success = False
			self.logger.info("Create configuration file %s " % (configuration_file_path))
			with open(configuration_file_path, 'w') as configuration_file:
				configuration_file.write("[global]\nDescription = Wi-Fi service configuration file. Generated by lib_wifi.py. Do not edit manually\n\n")
				configuration_file.write("[service_" + service_name + "]\n")
				configuration_file.write("Type = wifi\n")
				configuration_file.write("Name = " + ssid + "\n")
				configuration_file.write("SSID = " + service_hexssid + "\n")
				configuration_file.write("Security = " + self.service_security + "\n")
				for key in security_params_dict:
					configuration_file.write(key + " = " + security_params_dict[key] + "\n")
			configuration_file.close()
			lib_system.sync()
			self._bind_connman_to_wifi()	# Ensure connman is bound to wifi
			service = dbus.Interface(self.bus.get_object("net.connman", path), "net.connman.Service")
			self.service_auth_errors = 0
			# Execute connman Connect function. It can accept a keyword argument (timeout=x) as a parameter
			self._execute_signal_based_function(service.Connect, ({'timeout':10000}), ArgumentExpansion.DICTIONARY, timeout_sec=SIGNAL_CONNECTION_TIMEOUT_SEC, interface=WPAS_DBUS_INTERFACES_INTERFACE, signal_name="PropertiesChanged", signal_handler=self._signal_properties_changed)
			if self.signal_received:
				service.SetProperty("AutoConnect",True)
				success = True
				message = "Connected to %s" % (ssid)
			else:
				self._quit_event_loop()
				message = "Timeout while connecting to %s" % (ssid)
		except dbus.DBusException as e:
			self._quit_event_loop()
			# Find out and update error code
			service_error = "Unknown"
			try:
				# WPA2-PSK passphrase length error?
				if self.service_security == "psk" and "Not registered" in str(e):
					passprhase_length = len(security_params_dict["Passphrase"])
					if passprhase_length < PSK_PASSPHRASE_LENGTH_MIN or passprhase_length > PSK_PASSPHRASE_LENGTH_MAX:
						service_error = "Passphrase lenght out of bounds({}--{})".format(PSK_PASSPHRASE_LENGTH_MIN,PSK_PASSPHRASE_LENGTH_MAX)
						error_code = ConnectionError.INVALID_KEY
				# Other errors
				else:
					properties = service.GetProperties()
					if "Error" in properties:
						service_error = properties["Error"]
						if "invalid-key" in service_error:
							error_code = ConnectionError.INVALID_KEY
						elif "connect-failed" in service_error and self.service_auth_errors > 0:
							error_code = ConnectionError.AUTHENTICATION
			except:
				pass
			message = "DBus exception while connecting to {} on DBus: {}. service_error={} auth_errors={}, error_code={}".format(ssid, e, service_error, self.service_auth_errors, error_code)
		except Exception as e:
			self._quit_event_loop()
			message = "Generic exception while connecting to %s on DBus: %s" % (ssid, e)

		if configuration_file is not None and not configuration_file.closed:
			configuration_file.close()

		if success:
			error_code = ConnectionError.NO
			self.logger.info(message)
		else:
			self.logger.error(message)

		self.event_loop_thread.join(1)
		return (success, message, error_code)


	def reconnect(self, ssid):
		'''
		Reconnects to a service which is already registered
		A wifi service is considered as registered if its configuration file exists
		@ssid: ssid of the service to reconnect to
		Returns a tupple (success, message)
		'''
		self.logger.info("Reconnecting to %s..." % (ssid))

		# Get the wifi service. If first attempt fails, launch a scan and try a second one
		success, message, path, properties = self._find_service(ssid)
		if (path is None or not success):
			success, message = self._scan_wifi()
			if not success:
				return (success, message)
			success, message, path, properties = self._find_service(ssid)
			if (path is None or not success):
				return (success, message)

		try:
			success = False
			self._bind_connman_to_wifi()	# Ensure connman is bound to wifi
			service = dbus.Interface(self.bus.get_object("net.connman", path), "net.connman.Service")
			# Execute connman Connect function. It can accept a keyword argument (timeout=x) as a parameter
			self._execute_signal_based_function(service.Connect, ({'timeout':10000}), ArgumentExpansion.DICTIONARY, timeout_sec=SIGNAL_CONNECTION_TIMEOUT_SEC, interface=WPAS_DBUS_INTERFACES_INTERFACE, signal_name="PropertiesChanged", signal_handler=self._signal_properties_changed)
			if self.signal_received:
				service.SetProperty("AutoConnect",True)
				success = True
				message = "Reconnected to %s" % (ssid)
			else:
				self._quit_event_loop()
				message = "Timeout while reconnecting to %s" % (ssid)
		except dbus.DBusException as e:
			self._quit_event_loop()
			message = "DBus exception while reconnecting to {} on DBus: {}".format(ssid, e)
		except Exception as e:
			self._quit_event_loop()
			message = "Generic exception while reconnecting to %s on DBus: %s" % (ssid, e)

		if success:
			self.logger.info(message)
		else:
			self.logger.error(message)

		self.event_loop_thread.join(1)
		return (success, message)


	def disconnect(self, ssid):
		'''
		Disconnects from a service.
		Note that it doesn't remove its configuration file, so that if autoconnect is enabled, connection to this service can occur
		Use "remove" to disconnect from the service and remov its configuration file
		@ssid: ssid of the service to disconnect from
		Returns a tupple (success, message)
		'''
		self.logger.info("Disconnecting from %s..." % (ssid))

		# Get the wifi service
		success, message, path, properties = self._find_service(ssid)
		if (path is None or not success):
			return (success, message)

		success = False
		try:
			self._bind_connman_to_wifi()	# Ensure connman is bound to wifi
			service = dbus.Interface(self.bus.get_object("net.connman", path),"net.connman.Service")
			service.Disconnect()
			message = "Disconnected from %s" % (ssid)
			success = True
		except dbus.DBusException as e:
			message = "DBus exception while disconnecting from %s on DBus: %s" % (ssid, e)
		except Exception as e:
			message = "Generic exception while disconnection from %s on DBus: %s" % (ssid, e)

		if success:
			self.logger.info(message)
		else:
			self.logger.error(message)

		return (success, message)


	def remove(self, ssid):
		'''
		Removes a service, by removing its configuration file
		We assume that connman is running.
		If connman is running the associated configuration folder is automatically removed, otherwise it isn't
		@ssid: ssid of the service to be removed
		Returns a tupple (success, message)
		'''
		self.logger.info("Removing %s..." % (ssid))

		success = False
		encoded_ssid = encode_ssid(ssid)
		config_file_pattern = CONFIGURATION_FILES_PATH + ("/wifi_*_%s.config" % encoded_ssid)
		try:
			for filename in glob.glob(config_file_pattern):
				self.logger.info("Removing file %s" % (filename))
				os.remove(filename)
			lib_system.sync()
			message = "Service %s has been removed" % (ssid)
			success = True
		except Exception as e:
			message = "Generic exception while removing %s: %s" % (ssid, e)

		if success:
			self.logger.info(message)
		else:
			self.logger.error(message)

		return (success, message)


	def remove_all(self):
		'''
		Removes all services, by removing its configuration files and folders
		Returns a tupple (success, message)
		'''
		self.logger.info("Removing all services...")

		success = False
		config_file_patterns = [CONFIGURATION_FILES_PATH + ("/wifi_*_*.config"), CONFIGURATION_FILES_PATH + ("/_wifi_*_*.config_")]
		config_folder_patterns = [CONFIGURATION_FILES_PATH + ("/wifi_*_*_managed_*"), CONFIGURATION_FILES_PATH + ("/_wifi_*_*_managed_*")]
		try:
			for config_folder_pattern in config_folder_patterns:
				for directory in glob.glob(config_folder_pattern):
					self.logger.info("Removing folder %s" % (directory))
					rmtree(directory)

			for config_file_pattern in config_file_patterns:
				for filename in glob.glob(config_file_pattern):
					self.logger.info("Removing file %s" % (filename))
					os.remove(filename)

			lib_system.sync()
			message = "All services have been removed"
			success = True
		except Exception as e:
			message = "Generic exception while removing all services: %s" % (e)

		if success:
			self.logger.info(message)
		else:
			self.logger.error(message)

		return (success, message)


	def get_registered_service(self):
		'''
		Gets the registered wifi service
		A wifi service is considered as registered if its configuration file exists
		Returns a tupple (success, message, registered service)
			success: True or False
			message: information message
			registered service: a tuple (SSID, encoded SSID)
		'''
		self.logger.info("Getting registered service...")

		success = False
		try:
			registered_service = ()
			config_files_pattern = CONFIGURATION_FILES_PATH + "/wifi_*_*.config"
			for registered_service_file in glob.glob(config_files_pattern):
				(_, _, encoded_ssid) = get_properties_from_config_filename(registered_service_file)
				ssid = decode_ssid(encoded_ssid)
				registered_service = (ssid, encoded_ssid)
			if len(registered_service) is not 0:
				message = "Registered service: %s %s" % (ssid, encoded_ssid)
			else:
				message = "There is no registered service"
			success = True
		except Exception as e:
			message = "Generic exception while getting registered service: %s" % (e)

		if success:
			self.logger.info(message)
		else:
			self.logger.error(message)

		return (success, message, registered_service)


	def get_connection_status(self, log_enabled = True):
		'''
		Gets actual connetion status
		@log_enabled: if True the function will log, otherwise not.
		              This feature has been added to avoid logs every 3 seconds when the funciton is called from monitor_system.py
		Returns a tupple (success, connected, message, current_BSS, disconnect_reason)
			success: True or False
			connected: True or False
			message: information message
			current_BSS: the path to D-Bus object representing BSS which wpa_supplicant is associated with, or "/" if is not associated at all
			disconnect_reason: the most recent IEEE 802.11 reason code for disconnect. Negative value indicates locally generated disconnection
		'''
		properties = self._get_interface_properties(log_enabled)

		current_BSS = None
		disconnect_reason = None
		connected = False
		success = False
		state = None

		if "CurrentBSS" in properties:
			current_BSS = properties["CurrentBSS"]
		if "DisconnectReason" in properties:
			disconnect_reason = properties["DisconnectReason"]
		if "State" in properties:
			state = properties["State"]

		if (disconnect_reason == None) or (current_BSS == None):
			message = "Unable to read Wi-Fi interface properties"
			if log_enabled:
				self.logger.error(message)
		else:
			if (current_BSS == "/") or (disconnect_reason < 0) or (state != "completed"):
				message = "Wi-Fi is disconnected. CurrentBSS: %s DisconnectReason: %s State: %s" % (current_BSS, disconnect_reason, state)
			else:
				message = "Wi-Fi is connected. CurrentBSS: %s DisconnectReason: %s State: %s" % (current_BSS, disconnect_reason, state)
				connected = True
			success = True
			if log_enabled:
				self.logger.info(message)

		return (success, connected, message, current_BSS, disconnect_reason)


	def acquire_lock(self, timeout = -1):
		'''
		Tries to acquire a lock based on file lock mechanism
		@timeout: max timeout in seconds to wait for lock acquisition
			  if < 0, acquire the lock in blocking mode (default mode)
			  if 0, no timeout, just try to acquire the lock in non blocking mode

		Returns True on success, otherwise False
		'''
		if (timeout < 0):
			# Blocking mode
			return self._acquire_lock()
		elif (timeout == 0):
			# Non blocking mode
			return self._acquire_lock(False)
		else:
			# Timeout mode
			local_timeout = timeout
			while (local_timeout >= 0):
				if self._acquire_lock(False):		# Non blocking mode
					return True 			# lock acquired, return
				local_timeout = local_timeout - 1	# lock not acquired, retry
				sleep(1)
		return False


	def release_lock(self):
		'''
		Releases the lock, by closing the associated file
		'''
		if self.lock_file is not None and not self.lock_file.closed:
			fcntl.flock(self.lock_file,fcntl.LOCK_UN)
			self.lock_file.close()
