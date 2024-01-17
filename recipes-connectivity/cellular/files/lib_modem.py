#!/usr/bin/python3

import lib_system
import subprocess
import os
import shutil
import serial
import time
import dbus
import sys
import socket
import ctypes
import lib_network
import glob
import logging
import lib_logger
from enum import Enum
from collections import namedtuple

logger = logging.getLogger(__name__)
# Add default empty logger to let the user of the library use it without logger defined
logger.addHandler(logging.NullHandler())


CELLULAR_INTERFACE_NAME = "ppp0"

OFONO_SERVICE = "ofono.service"
CONNMAN_SERVICE = "connman.service"
CELLULAR_DATA_SUPERVISOR_TIMER = "cellular_data_supervisor.timer"
CELLULAR_DATA_SUPERVISOR_SERVICE = "cellular_data_supervisor.service"
CELLULAR_SIGNAL_STRENGTH_MONITOR_SERVICE = "cellular_signal_strength_monitor.service"


# all stuff containing information on USB modems
USBModemInfo = namedtuple("USBModemInfo", "Name VidPid")

"""List of all USB modems supported by the system. Add here any further amazing modem.

On USBCFG the ProductId of a telit modem can change.
Per default/factory-config, telit modems will report as productId 0x0036 (ACM + NCM).
USBCFG value of '2' will be set automatically for Multitech modems by ofono, which
will put the modem into 'enterprise'-/acm-only mode which reports as 0x0035.
USBCFG value of '4' actually sets the Modems into ACM + NCM + Suspend mode, which
reports as 0x0037.
"""
__supported_modems = [
	USBModemInfo("Multitech/Telit", "1bc7:0035"),
	USBModemInfo("Multitech/Telit", "1bc7:0036"),
	USBModemInfo("Multitech/Telit", "1bc7:0037"),
]

class ModemDiagnosticCode(Enum):
	WellConfigured = 0
	ModemIsAbsent = 10
	SeveralModemsArePresent = 11
	OfonodNotRunning = 15
	ModemIsNotRecognized = 20
	SimIsAbsent = 25
	SimIsPinLocked = 30
	SimIsPukLocked = 35
	SimError = 40
	NetworkIsUnregistered = 45
	GPRSNetworkNotRegistered = 50
	APNConnectionFailed = 55
	InternetContextFailed = 60
	ContactServerFailed = 65
	SwitchFirmwareFailed = 70
	ConfigureTechnologyFailed = 75

# DBus data conversion stuff
_dbus2py = {
	dbus.String : str,
	dbus.UInt32 : int,
	dbus.Int32 : int,
	dbus.Int16 : int,
	dbus.UInt16 : int,
	dbus.UInt64 : int,
	dbus.Int64 : int,
	dbus.Byte : int,
	dbus.Boolean : bool,
	dbus.ByteArray : str,
	dbus.ObjectPath : str
}

def __dbus2py(d):
	"""DBus data conversion stuff
	"""
	t = type(d)
	if t in _dbus2py:
		return _dbus2py[t](d)
	if t is dbus.Dictionary:
		return dict([(__dbus2py(k), __dbus2py(v)) for k, v in list(d.items())])
	if t is dbus.Array and d.signature == "y":
		return "".join([chr(b) for b in d])
	if t is dbus.Array or t is list:
		return [__dbus2py(v) for v in d]
	if t is dbus.Struct or t is tuple:
		return tuple([__dbus2py(v) for v in d])
	return d

def getConfigModemFilePath():
	"""path to the file containing modem configuration file
	"""
	return "/media/persistent/system/config_modem"

def loadConfigModemFile(verbose=True):
	""" return modem configuration file content
		e.g. True, PIN, APN, UserName, Password, FWMode or False, "", "", "", "", ""

		Note: FWMode is only relevant for North America modem. It should always be "" for other modem types
	"""
	config_modem_file_path = getConfigModemFilePath()
	if verbose:
		logger.info("")
		logger.info("-Load existing modem configuration from \"%s\"" % (config_modem_file_path))

	if os.path.isfile(config_modem_file_path):
		# read modem configuration file
		try:
			with open(config_modem_file_path, 'r') as config_modem_file:
				config_modem_lines = config_modem_file.read().splitlines()
				if len(config_modem_lines) == 4:
					return True, config_modem_lines[0], config_modem_lines[1], config_modem_lines[2], config_modem_lines[3], ""
				elif len(config_modem_lines) >= 5:
					return True, config_modem_lines[0], config_modem_lines[1], config_modem_lines[2], config_modem_lines[3], config_modem_lines[4]
				else:
					message = "File content is corrupted"
		except Exception as e:
			message = "Exception while reading \"%s\": \"%s\"" % (config_modem_file_path, e)
	else:
		message = "No modem configuration"
	if verbose:
		logger.info(message)
	return False, "","","","",""

def saveConfigModemFile(PIN, APN, user_name, password, fwmode="", verbose=False):
	""" save modem configuration into modem configuration file
		e.g. 	PIN
				APN
				UserName
				Password
		in /media/persistent/system/config_modem

		In case of a North America modem, a fifth line can be added to specify what modem firmware to use ("att" or "verizon")
	"""
	config_modem_file_path = getConfigModemFilePath()

	if verbose:
		logger.info("")
		logger.info("-Save modem configuration to \"%s\"" % (config_modem_file_path))

	status = False
	try:
		config_modem_lines = "%s\n%s\n%s\n%s\n" % (PIN, APN, user_name, password)
		if fwmode != "":
			config_modem_lines += fwmode + "\n"

		with open(config_modem_file_path, 'w') as config_modem_file:
			config_modem_file.write(config_modem_lines)
			message = "Configuration saved"
			status = True
	except Exception as e:
		message = "Exception while writing \"%s\": \"%s\"" % (config_modem_file_path, e)
	if verbose:
		logger.info(message)
	return status, message

def isModemConfigured():
	if os.path.isfile(getConfigModemFilePath()):
		return True
	return False

def removeConfigModemFile():
	"""Remove configuration file from permanent memory (if any)
	"""
	try:
		os.remove(getConfigModemFilePath())
		logger.info("Removed config file %s" % (getConfigModemFilePath()))
	except OSError:
		pass

	lib_system.sync()

def listUSBModems(verbose=False):
	""" Return list of supported USB modems currently mounted by the system.
	tuple (count, message, list)
	"""

	if verbose:
		logger.info("")
		logger.info("-Check for compatible USB modem(s)")

	count = 0
	mounted_modems = []
	message = "No modem found"

	# We search modems mounted by the system
	for supported_modem in __supported_modems:
		try:
			# check if this modem exists in the system using lsusb command (searched by vendor Id & product Id)
			command = ['lsusb', '-d', supported_modem.VidPid]
			with open(os.devnull, 'w') as shutup:
				subprocess.check_call(command, stdout=shutup, stderr=shutup)
			count += 1
			mounted_modems.append(supported_modem)

			message = "Modem \'%s\' is detected" % (supported_modem.Name)
			if verbose:
				logger.info(message)

		except subprocess.CalledProcessError as e:
			# this exception is raised when lusb commands failed to find a specific device
			# in this case we look for the next one
			pass
		except Exception as e:
			if verbose:
				logger.error("Generic exception while getting USB modem(s):%s" % (e))
			break
	if count > 1:
		message = "Several modems are installed"
	if verbose and count != 1:
		logger.info(message)

	return count, message, mounted_modems

def sendSerialCommandToModem(command, read_timeout = 1):
	""" Send a command to the modem via serial line. return tuple (status, modem answer or error message)
	Note: As it directly opens modem serial port, this function cannot be called when ofono is running...
	"""
	if len(command) == 0:
		return False, "Command to send is empty"

	try:
		ser = serial.Serial(
			port='/dev/ttyACM0',
			baudrate=115200,
			timeout=read_timeout,	#read timeout
			write_timeout=1,	#write timeout
			parity=serial.PARITY_ODD,
			stopbits=serial.STOPBITS_TWO,
			bytesize=serial.SEVENBITS
		)
	except serial.SerialException as e:
		return False, "Exception while creating serial communication with modem %s" % (e)

	try:
		answer = ''
		one_line = ''

		# send the command and retrieve the answer sent by the modem
		ser.write(command.encode())
		ser.flush()

		# read on serial until empty line
		while True:
			one_line = ser.readline().decode("utf-8")
			if len(one_line) == 0:
				break
			answer+=one_line
		ser.close()

	except Exception as e:
		ser.close()
		return False, "Exception sending/reading serial command to the modem : %s" % (e)

	return True, answer

def checkModemReadyForATCommands(verbose = False):
	""" Send a basic AT command to the modem in order to validate that the modem is ready to exchange some AT commands, return tuple (status, message)
	Note: As it directly opens modem serial port, this function cannot be called when ofono is running...
	"""

	if verbose:
		logger.info("")
		logger.info("-Check modem ready for AT command")

	# send basic AT command that retrieves modem serial number
	# we don't care about the returned serial number itself; 'OK' in the answer is good enough to determine that it is ready for some AT commands
	serial_command_status, modem_answer = sendSerialCommandToModem("AT+CGMR\r")

	status = False
	message = ""

	if serial_command_status:
		if len(modem_answer) == 0 or modem_answer.find('OK') == -1:
			message = "Modem is frozen or answered wrongly"
		else:
			status = True
			message = "Modem is ready for AT commands"
	else:
		message = modem_answer

	if verbose:
		logger.info(message)

	return status, message

def loadModemFactoryConfiguration(verbose = False):
	""" Set modem configuration to "Factory-Defined Configuration".
	It sets the configuration parameters to default values specified by manufacturer.
	Both the factory profile base section and the extended section are considered (full factory profile).
	Note: As it directly opens modem serial port, this function cannot be called when ofono is running...
	"""

	if verbose:
		logger.info("")
		logger.info("-Load modem factory-defined configuration")

	# Factory defined configuration is set by sending a specific AT command
	# increase read timeout as this command is longer to execute
	serial_command_status, modem_answer = sendSerialCommandToModem("AT&F1\r", 2)

	status = False
	message = ""

	if serial_command_status:
		if len(modem_answer) == 0:
			message = "No answer from modem"
		elif modem_answer.find('OK') == -1:
			message = "Bad answer from modem"
		else:
			status = True
			message = "Factory configuration applied"
	else:
		message = modem_answer

	if verbose:
		logger.info(message)

	return status, message

def logModemDiagnosticInformation():
	""" Log a set of information from modem for diagnostic purpose
	Note: As it directly opens modem serial port, this function should not be called when ofono is running...
	"""

	logger.info("")
	logger.info("-Collect modem diagnostic information")

	# check ofonod is not running
	ofonod_running, _ = isOfonodRunning()
	if ofonod_running:
		logger.warning("Cannot collect modem information as Ofonod process is running")
		return

	# check modem is ready for AT commands, wait a bit and retry if necessary
	modem_ready_for_AT_commands, message = __retryFunction(checkModemReadyForATCommands, None, False, 5, 1)
	logger.info(message)
	if not modem_ready_for_AT_commands:
		return

	# list of AT commands executed on modem to build diagnostic
	commands_to_execute = [
		("Set Echo", "ATE1\r"),
		("Set Verbose", "AT+CMEE=2\r"),
		("Model", "AT+CGMM\r"),
		("Serial", "AT+CGSN\r"),
		("Version", "AT+CGMR\r"),
		("Mode of operation", "AT+CEMODE?\r"),
		("Phone Functionality", "AT+CFUN?\r"),
		("SIM PIN status", "AT+CPIN?\r"),
		("IMSI", "AT+CIMI\r"),
		("GPRS Attachment state", "AT+CGATT?\r"),
		("Network registration", "AT+CREG?\r"),
		("GPRS Network Registration", "AT+CGREG?\r"),
		("LTE Network Registration", "AT+CEREG?\r"),
		("Operator", "AT+COPS?\r"),
		("Signal", "AT+CSQ\r")
	]

	try:
		# execute and log results for each AT command
		for command in commands_to_execute:
			# Extract from "LE910 AT Commands Reference Guide" : "The time needed to process the given command and return the response varies, depending on the command type.
			# Commands that do not interact with the SIM or the network, and only involve internal setups or readings, have an immediate response"
			# I decreased default timeout to 500ms (15 times longer than observed response time)
			_, modem_answer = sendSerialCommandToModem(command[1], 0.5)
			logger.info(command[0] + ": " + modem_answer)
	except Exception as e:
		logger.info("Exception while collecting diagnostic information from modem")

def rebootModemHard():
	""" Perform a hard reboot on modem connected to external USB box.
	"""
	logger.info("")
	logger.info("-Reboot USB modem (hard)")

	try:
		# call a dedicated sh script to perform this hard reset
		command = ['reboot_modem.sh']
		with open(os.devnull, 'w') as shutup:
			subprocess.check_call(command, stdout=shutup, stderr=shutup)

	except Exception as e:
		return False, "exception hard rebooting modem:%s" % (e)

	return True, "modem rebooted (hard)"

def rebootCurrentModem():
	"""look for USB modem currently mounted on the system and reboot it. This is a soft reset.
	"""

	# look for a compatible modem on the system and reboot-it
	mounted_modems_count, mounted_modems_message, mounted_modems_list = listUSBModems(False)
	if mounted_modems_count == 1:
		ids = mounted_modems_list[0][1].split(":")
		int_idVendor = int(ids[0], 16)
		int_idProduct = int(ids[1], 16)
		return rebootUSbDeviceModem(int_idVendor, int_idProduct)

	logger.info("")
	logger.info("Error while detecting modem to reboot: %s" % (mounted_modems_message))

	return False, mounted_modems_message

def rebootUSbDeviceModem(idVendor, idProduct):
	"""reboot the external modem by the resetUsbDevice function from libusb library. This is a soft reset.
	"""

	logger.info("")
	logger.info("-Reboot USB modem (soft)")

	modem_library_name = 'libModem.so'
	try:
		# External modem reboot is done by using a dedicated C library
		modem_lib = ctypes.CDLL(modem_library_name)
		modem_lib.ResetUsbDevice(idVendor, idProduct)

		# wait a bit to let the modem reboot
		time.sleep(10)

		return True, "Reboot is done"
	except Exception as e:
		logger.exception("Exception while rebooting USB modem:%s" % (e))
		pass
	return False, "Exception while rebooting USB modem:%s" % (e)

def restartConnman():
	return lib_system.restartService(CONNMAN_SERVICE)

def startOfonod():
	return lib_system.startService(OFONO_SERVICE)

def stopOfonod():
	success, message = lib_system.stopService(OFONO_SERVICE)

	if success:
		# At this point, the request to stop ofono.service has been sent to systemd, which then sends a SIGTERM to ofonod.
		# But ofonod can take some time to complete its shutdown after a SIGTERM. Therefore, we wait at most 30 seconds
		# for it to exit. It usually takes between 5 and 10 seconds to shutdown completely.
		# This is important to wait for ofonod to be terminated so that its configuration files, as well as
		# connman's configuration files related to cellular, can be cleared properly when needed.
		max_wait_time = 30
		while isOfonodRunning()[0] and max_wait_time > 0:
			time.sleep(1)
			max_wait_time -= 1

		if isOfonodRunning()[0]:
			success = False
			message += " but ofonod is still running"

	return success, message


def enableOfonod():
	return lib_system.enableService(OFONO_SERVICE)

def disableOfonod():
	return lib_system.disableService(OFONO_SERVICE)

def startCellularDataSupervisor():
	return lib_system.startService(CELLULAR_DATA_SUPERVISOR_TIMER)

def stopCellularDataSupervisor():
	# Stopping both the timer and the service to ensure that the cellular supervisor
	# is really not running anymore when this function returns.
	# The timer is stopped first to ensure that it won't trigger a new run of the supervisor.
	timer_success, timer_message = lib_system.stopService(CELLULAR_DATA_SUPERVISOR_TIMER)
	service_success, service_message = lib_system.stopService(CELLULAR_DATA_SUPERVISOR_SERVICE)

	success = timer_success and service_success
	message = timer_message + " and " + service_message

	return success, message

def enableCellularDataSupervisor():
	return lib_system.enableService(CELLULAR_DATA_SUPERVISOR_TIMER)

def disableCellularDataSupervisor():
	return lib_system.disableService(CELLULAR_DATA_SUPERVISOR_TIMER)

def startCellularSignalStrengthMonitor():
	return lib_system.startService(CELLULAR_SIGNAL_STRENGTH_MONITOR_SERVICE)

def stopCellularSignalStrengthMonitor():
	return lib_system.stopService(CELLULAR_SIGNAL_STRENGTH_MONITOR_SERVICE)

def enableCellularSignalStrengthMonitor():
	return lib_system.enableService(CELLULAR_SIGNAL_STRENGTH_MONITOR_SERVICE)

def disableCellularSignalStrengthMonitor():
	return lib_system.disableService(CELLULAR_SIGNAL_STRENGTH_MONITOR_SERVICE)

def __getModemsFromDBus(bus):
	"""retrieve modems on DBus.
	"""
	modems = None
	message = ""
	try:
		manager = dbus.Interface(bus.get_object('org.ofono', '/'), 'org.ofono.Manager')
		modems = manager.GetModems()
		number = len(modems)
		if number == 0:
			modems = None
			message = "No modem found on DBus"
		else:
			message = "%d modem(s) found on DBus" % (number)
	except dbus.DBusException as e:
		modems = None
		message = "DBus exception while getting modems on DBus:%s" % (e)
	except Exception as e:
		modems = None
		message = "Generic exception while getting modems on DBus:%s" % (e)
	return modems, message

def __retryFunction(function, bus, verbose, attempts, delay):
	""" call repeatedly a function given in parameter. A delay is applied between each call.
	It returns when the result of the called function is True or when the maximum of attempts is reached
	"""
	for attempt in range(0,attempts):
		if attempt > 0:
			time.sleep(delay)
			if verbose:
				logger.info("")
				logger.info("-Attempt #%d->" % (attempt+1))
		if bus is None:	# this function does not require any bus
			status, message = function(verbose)
		else:
			status, message = function(bus, verbose)
		if status:
			break	#success, no need to retry anymore
	return status, message

def isModemOnDBus(bus, verbose=False, attempts=1, delay=5):
	return __retryFunction(__isModemOnDBus, bus, verbose, attempts, delay)

def __isModemOnDBus(bus, verbose):
	""" Check if the modem is visible on ofono DBus
	"""
	if verbose:
		logger.info("")
		logger.info("-Check for presence of modem on DBus")

	status = False
	modems, message = __getModemsFromDBus(bus)
	if modems != None:
		status = True
	if verbose:
		logger.info(message)
	return status, message

def isSimPresent(bus, verbose=False, attempts=1, delay=5):
	return __retryFunction(__isSimPresent, bus, verbose, attempts, delay)

def __isSimPresent(bus, verbose):
	""" retrieve Sim status (present or not)
	"""
	if verbose:
		logger.info("")
		logger.info("-Check for presence of Sim card")

	present = False

	modems, message = __getModemsFromDBus(bus)
	if modems != None:
		# we suppose there is only one modem connected
		modem_path = modems[0][0]

		present = False
		try:
			sim_manager = dbus.Interface(bus.get_object('org.ofono', modem_path),'org.ofono.SimManager')
			present = __dbus2py(sim_manager.GetProperties()['Present'])
			if present:
				message = "Sim is present"
			else:
				message = "Sim is absent"

		except dbus.DBusException as e:
			message = "DBus exception while checking presence of Sim card:%s" % (e)
		except KeyError as e:
			message = "KeyError exception: %s not present on Dbus" % (e)
		except Exception as e:
			message = "Generic exception while checking presence of Sim card:%s" % (e)

	if verbose:
		logger.info(message)
	return present, message

class PinStatus(Enum):
	Unknown = 0
	PinIsRequired = 1
	PukIsRequired = 2
	PinIsValidOrNotRequired = 3

def getPinStatus(bus, verbose=False):
	""" retrieve Pin status (returns PinStatus enum)
	"""

	if verbose:
		logger.info("")
		logger.info("-Get Pin status")

	status = PinStatus.Unknown

	modems, message = __getModemsFromDBus(bus)
	if modems != None:
		# we suppose there is only one modem connected
		modem_path = modems[0][0]

		try:
			sim_manager = dbus.Interface(bus.get_object('org.ofono', modem_path), 'org.ofono.SimManager')
			sim_pin_required = __dbus2py(sim_manager.GetProperties()['PinRequired'])
			if sim_pin_required == "none":
				message = "Pin is valid or not required"
				status = PinStatus.PinIsValidOrNotRequired
			elif sim_pin_required == "puk":
				message = "A Puk is required"
				status = PinStatus.PukIsRequired
			else:
				message = "A Pin is required"
				status = PinStatus.PinIsRequired
		except dbus.DBusException as e:
			message = "DBus exception while getting Pin status:%s" % (e)
		except KeyError as e:
			message = "KeyError exception: %s not present on Dbus" % (e)
		except Exception as e:
			message = "Generic exception while getting Pin status:%s" % (e)

	if verbose:
		logger.info(message)
	return status, message

class DisablePinAnswer(Enum):
	Unknown = 0
	Success = 1
	WrongPin = 2

def disablePin(bus, pin, verbose=False):
	"""Enter a Pin and disable it. Sim must be locked by a Pin before. Exception otherwise
	"""

	if verbose:
		logger.info("")
		logger.info("-Enter and disable Pin using %s" % (pin))

	status = DisablePinAnswer.Unknown

	modems, message = __getModemsFromDBus(bus)
	if modems != None:
		modem_path = modems[0][0]

		try:
			sim_manager = dbus.Interface(bus.get_object('org.ofono', modem_path), 'org.ofono.SimManager')
			sim_manager.EnterPin("pin", pin)
			sim_manager.UnlockPin("pin", pin)
			message = "Pin entered and disabled"
			status = DisablePinAnswer.Success
		except dbus.DBusException as e:
			#In case of wrong pin e is: "org.ofono.Error.Failed: Operation failed"
			#In case of no pin required e is: "org.ofono.Error.InvalidFormat: Argument format is not recognized"
			if str(e) == "org.ofono.Error.Failed: Operation failed":
				status = DisablePinAnswer.WrongPin
				message = "Wrong Pin"
			else:
				message = "DBus exception while entering/disabling pin:%s" % (e)
		except Exception as e:
			message = "Generic exception while entering/disabling pin:%s" % (e)

	if verbose:
		logger.info(message)
	return status, message

def getServiceProviderName(bus, verbose=False, attempts=1, delay=5):
	return __retryFunction(__getServiceProviderName, bus, verbose, attempts, delay)

def __getServiceProviderName(bus, verbose):
	""" retrieve Service Provicer Name
	"""

	if verbose:
		logger.info("")
		logger.info("-Get Service Provider Name")

	service_provider_name = ""

	modems, message = __getModemsFromDBus(bus)
	if modems != None:
		# we suppose there is only one modem connected
		modem_path = modems[0][0]

		try:
			sim_manager = dbus.Interface(bus.get_object('org.ofono', modem_path), 'org.ofono.SimManager')
			service_provider_name = __dbus2py(sim_manager.GetProperties()['ServiceProviderName'])
			message = "Service Provider Name is \'%s\'" % (service_provider_name)
		except dbus.DBusException as e:
			message = "DBus exception while getting Service Provider Name:%s" % (e)
		except KeyError as e:
			"""Set service_provider_name to 'Unknown' if we can not get the real value from the SimManager
			interface. So far this has only been observed on Verizon-LTE and will only happen if GPRS is not
			registered in the classical way.
			When extending this function, keep in mind that this exception branch captures all dict-KeyErrors.
			"""
			service_provider_name = 'Unknown'
			message = "Service Provider Name is \'Unknown\' (most likely Verizon)"
		except Exception as e:
			message = "Generic exception while getting Service Provider Name:%s" % (e)

	if verbose:
		logger.info(message)

	return service_provider_name, message

def enumerateModems(bus):
	"""Print all information accessible from ofono DBus regarding modems and their Sim
	"""

	logger.info("")
	logger.info("-Enumerate modems")

	modems, message = __getModemsFromDBus(bus)
	if modems == None:
		logger.info(message)
		return

	for path, properties in modems:
		logger.info(("[ %s ]" % (path)))

		for key in list(properties.keys()):
			if key in ["Interfaces", "Features"]:
				val = ""
				for i in properties[key]:
					val += i + " "
			else:
				val = properties[key]
			logger.info(("    %s = %s" % (key, val)))

		for interface in properties["Interfaces"]:
			# Skip requesting of properties for (slow) Call* interfaces
			if 'Call' in interface:
				continue

			object = dbus.Interface(bus.get_object('org.ofono', path), interface)

			logger.info(("    [ %s ]" % (interface)))

			try:
				properties = object.GetProperties()
				for key in list(properties.keys()):
					if key in ["Calls",	"MultipartyCalls", "EmergencyNumbers", "SubscriberNumbers", "PreferredLanguages", "PrimaryContexts", "LockedPins", "Features", "AvailableTechnologies"]:
						val = ""
						for i in properties[key]:
							val += i + " "
					elif key in ["ServiceNumbers"]:
						val = ""
						for i in properties[key]:
							val += "[" + i + "] = '"
							val += properties[key][i] + "' "
					elif key in ["MobileNetworkCodeLength",	"VoicemailMessageCount", "MicrophoneVolume", "SpeakerVolume", "Strength", "DataStrength", "BatteryChargeLevel"]:
						val = int(properties[key])
					elif key in ["MainMenu"]:
						val = ", ".join([ text + " (" + str(int(icon)) + ")" for text, icon in properties[key] ])
					elif key in ["Retries"]:
						val = ""
						for i in properties[key]:
							val +=  "[" + i + " = "
							val += str(int(properties[key][i])) + "] "
					elif key in ["Settings"]:
						val = "{"
						for i in list(properties[key].keys()):
							val += " " + i + "="
							if i in ["DomainNameServers"]:
								for n in properties[key][i]:
									val += n + ","
							else:
								val += properties[key][i]
						val += " }"
					else:
						val = properties[key]
					logger.info(("        %s = %s" % (key, val)))
			except:
				continue
		logger.info('')

def isCellularNetworkRegistered(bus, verbose=False, attempts=1, delay=5):
	return __retryFunction(__isCellularNetworkRegistered, bus, verbose, attempts, delay)

def __isCellularNetworkRegistered(bus, verbose):
	""" retrieve cellular network registration status (registered or not)
	"""

	if verbose:
		logger.info("")
		logger.info("-Check for cellular network registration")

	status = False

	modems, message = __getModemsFromDBus(bus)
	if modems != None:
		modem_path = modems[0][0]

		try:
			# retrieve org.ofono.NetworkRegistration.Status property: The current network registration status of the modem
			# doc: The possible values are:
			#	"unregistered"  Not registered to any network
			#	"registered"    Registered to home network
			#	"searching"     Not registered, but searching
			#	"denied"        Registration has been denied
			#	"unknown"       Status is unknown
			#	"roaming"       Registered, but roaming
			network_registration_interface = dbus.Interface(bus.get_object('org.ofono', modem_path),'org.ofono.NetworkRegistration')
			network_registration_status = __dbus2py(network_registration_interface.GetProperties()['Status'])
			message = "Cellular network is %s" % (network_registration_status)
			if network_registration_status == "registered" or network_registration_status == "roaming":
				status = True
			else:
				"""If NetworkRegistration interface is not set to registered/roaming it is still possible that we are able to connect
				via plain LTE. To verify we are checking the ConnectionsManagers bearer (needs to be 'lte') and the corresponding
				'attached' value (needs to be 'true'/'1').
				So far, this kind of LTE behavior was only seen on provider 'Verizon'.
				"""
				connection_manager_interface = dbus.Interface(bus.get_object('org.ofono', modem_path),'org.ofono.ConnectionManager')
				connection_manager_bearer = __dbus2py(connection_manager_interface.GetProperties()['Bearer'])
				connection_manager_attached = __dbus2py(connection_manager_interface.GetProperties()['Attached'])
				if connection_manager_bearer.lower() == 'lte' and connection_manager_attached:
					message = "Cellular network is registered via native LTE"
					status = True
		except dbus.DBusException as e:
			message = "DBus exception while checking for network resgistration:%s" % (e)
		except KeyError as e:
			message = "KeyError exception: %s not present on Dbus" % (e)
		except Exception as e:
			message = "Generic exception while checking for network resgistration:%s" % (e)

	if verbose:
		logger.info(message)
	return status, message

def isDataNetworkRegistered(bus, verbose=False, attempts=1, delay=5):
	return __retryFunction(__isDataNetworkRegistered, bus, verbose, attempts, delay)

def __isDataNetworkRegistered(bus, verbose):
	""" retrieve data network registration status (registered or not)
	"""

	if verbose:
		logger.info("")
		logger.info("-Check for data network registration")

	status = False

	modems, message = __getModemsFromDBus(bus)
	if modems != None:
		modem_path = modems[0][0]

		try:
			# retrieve org.ofono.ConnectionManager.Attached property: Contains whether the Packet Radio Service is attached
			# doc: "If this value changes to false, the user can assume that all contexts have been deactivated"
			# doc: "If the modem is detached, certain features will not be available, e.g. receiving SMS over packet radio or network initiated PDP activation."
			connection_manager_interface = dbus.Interface(bus.get_object('org.ofono', modem_path),'org.ofono.ConnectionManager')
			gprs_attached = __dbus2py(connection_manager_interface.GetProperties()['Attached'])
			if gprs_attached:
				status = True
				message = "Attached to GPRS/3G/4G network"
			else:
				message = "Not attached to any GPRS/3G/4G network"
		except dbus.DBusException as e:
			message = "DBus exception while checking for data network resgistration:%s" % (e)
		except KeyError as e:
			message = "KeyError exception: %s not present on Dbus" % (e)
		except Exception as e:
			message = "Generic exception while checking for data network resgistration:%s" % (e)

	if verbose:
		logger.info(message)
	return status, message

def isRoamingAllowed(bus, verbose=False, attempts=1, delay=5):
	return __retryFunction(__isRoamingAllowed, bus, verbose, attempts, delay)

def __isRoamingAllowed(bus, verbose):
	""" retrieve roaming allowed status (roaming allowed or not)
	"""

	if verbose:
		logger.info("")
		logger.info("-Check for roaming allowed")

	status = False

	modems, message = __getModemsFromDBus(bus)
	if modems != None:
		modem_path = modems[0][0]

		try:
			# retrieve org.ofono.ConnectionManager.RoamingAllowed property
			connection_manager_interface = dbus.Interface(bus.get_object('org.ofono', modem_path),'org.ofono.ConnectionManager')
			roaming_allowed = __dbus2py(connection_manager_interface.GetProperties()['RoamingAllowed'])
			if roaming_allowed:
				status = True
				message = "Roaming is allowed"
			else:
				message = "Roaming is not allowed"
		except dbus.DBusException as e:
			message = "DBus exception while reading Roaming allowed status:%s" % (e)
		except KeyError as e:
			message = "KeyError exception: %s not present on Dbus" % (e)
		except Exception as e:
			message = "Generic exception while reading Roaming allowed status:%s" % (e)

	if verbose:
		logger.info(message)
	return status, message


def setRoamingAllowed(bus, roamingAllowed=True):
	"""
	In ofono DBUS: "org.ofono.NetworkRegistration.Status == roaming" as soon as the SIM is not in the country of the service provider.
	In this case the modem is attached to a local network for voice only.
	It is necessary to set "org.ofono.ConnectionManager.RoamingAllowed to 1" to enable DATA roaming (GPRS, 3G, 4G)... this is the goal of this function
	"""

	logger.info("")
	if roamingAllowed:
		logger.info("-Enable data roaming")
	else:
		logger.info("-Disable data roaming")

	status = False

	modems, message = __getModemsFromDBus(bus)
	if modems != None:
		modem_path = modems[0][0]

		try:
			# retrieve org.ofono.ConnectionManager.RoamingAllowed property
			connection_manager_interface = dbus.Interface(bus.get_object('org.ofono', modem_path),'org.ofono.ConnectionManager')
			connection_manager_interface.SetProperty("RoamingAllowed", dbus.Boolean(roamingAllowed))
			status = True
		except dbus.DBusException as e:
			message = "DBus exception while setting RoamingAllowed:%s" % (e)
		except Exception as e:
			message = "Generic exception while setting RoamingAllowed:%s" % (e)
	return status, message

def getSignalStrength(bus, verbose=False):
	"""
	retrieve the signal strength of the connected modem.
	based on the technologie used (Edge, 3G, 4G,...) the signal strength value
	is stored in a different key, (RSSI = 3G, RSRP = 4G,...)
	we therefore return appropriate the strength value based on the technologie but also the tech itself
	"""
	if verbose:
		logger.info("")
		logger.info("-Get signal strength")

	# this value indicates a failure in signal strength reading
	strength = -1
	tech = 'none'
	# it is mandatory to be registered to a network to have access to signal strength propertie in DBus
	network_registered, message = isCellularNetworkRegistered(bus)
	# the known signal strength value based on technologie
	#3G
	rssi = -1
	#4G
	rsrp = -1

	if network_registered:
		modems, message = __getModemsFromDBus(bus)
		if modems != None:
			modem_path = modems[0][0]

			try:
				#manager = dbus.Interface(bus.get_object('org.ofono', '/'), 'org.ofono.Manager')
				#modems = manager.GetModems()
				#path = modems[0][0]

				tdn = dbus.Interface(bus.get_object('org.ofono', modem_path), 'org.ofono.TelitDataNetwork')
				status = tdn.GetRFStatus()
				for key in status.keys():
					if key == 'RSSI':
						rssi = int(status[key])
					if key == 'Tech':
						tech = str(status[key])
					if key == 'RSRP':
						rsrp = int(status[key])
#				TO KEEP as this might be usefull again
#				retrieve the interface containing the signal strength (org.ofono.NetworkRegistration)
#				network_registration_interface = dbus.Interface(bus.get_object('org.ofono', modem_path),'org.ofono.NetworkRegistration')
#				network_registration_properties = network_registration_interface.GetProperties()
#				length = len(network_registration_properties)
#				if length > 5 and (not 'Strength' in network_registration_properties) and wait:
#					#print "Start of ugly patch to retrieve the missing signal strength propertie on DBus"
#
#					# This is a ugly patch to solve bug FCON-1235:
#					# Sometimes org.ofono.NetworkRegistration.Strength propertie is not available but all other properties from org.ofono.NetworkRegistration are available
#					# normally org.ofono.NetworkRegistration interface contains 9 properties, only 8 when Strength is missing...
#					# The fact to list properties from org.ofono.CallBarring and org.ofono.CallSettings make org.ofono.NetworkRegistration.Strength available again on DBus...
#
#					#Most of the time this bug occurs right after modem configuration or ofono.service restart
#					#let some long seconds before reading many properties on DBus that put ofono in failure...
#					#the happyness of using open source code...
#					time.sleep(10)
#
#					call_barring_interface = dbus.Interface(bus.get_object('org.ofono', modem_path),'org.ofono.CallBarring')
#					call_barring_properties = call_barring_interface.GetProperties()
#
#					call_settings_interface = dbus.Interface(bus.get_object('org.ofono', modem_path),'org.ofono.CallSettings')
#					call_settings_properties = call_settings_interface.GetProperties()
#
#					# ask again for these properties
#					network_registration_interface = dbus.Interface(bus.get_object('org.ofono', modem_path),'org.ofono.NetworkRegistration')
#					network_registration_properties = network_registration_interface.GetProperties()
#
#					#print "End of ugly patch to retrieve the missing signal strength value on DBus"
#				#strength = __dbus2py(network_registration_properties['Strength'])
#				#message = "Signal strength is %d%%" % (strength)
			except dbus.DBusException as e:
				message = "DBus exception while getting signal strength:%s" % (e)
			except KeyError as e:
				message = "Impossible to get signal strength right now"
			except Exception as e:
				message = "Generic exception while getting signal strength:%s" % (e)
	if verbose:
		logger.info(message)

	# if the current tech used is 4G we use for strength the rsrp
	# else we will use the rssi
	strength = rsrp if tech == "4G" else rssi

	return strength, message, tech

def clearInternetContext(bus):
	""" Clear existing internet context in Sim.
	"""

	logger.info("")
	logger.info("-Clear existing internet context")

	modems, message = __getModemsFromDBus(bus)
	if modems == None:
		logger.info(message)
		return

	try:
		for path, properties in modems:
			if "org.ofono.ConnectionManager" not in properties["Interfaces"]:
				continue

			connman = dbus.Interface(bus.get_object('org.ofono', path), 'org.ofono.ConnectionManager')
			contexts = connman.GetContexts()

			# remove existings contexts
			for path, properties in contexts:
				connman.RemoveContext(path)
				logger.info(("Removed: [ %s ]" % (path)))
		return

	except dbus.DBusException as e:
		message = "DBus exception while clearing internet contexts:%s" % (e)
	except Exception as e:
		message = "Generic exception while clearing internet contexts:%s" % (e)

def setInternetContext(bus, apn, user_name, password):
	""" Configure APN settings by creating an "Internet context" (stored in Sim)
	"""

	logger.info("")
	if len(apn) > 0:
		logger.info("-Configure internet context using %s" % (apn))
	else:
		logger.info("-Configure internet context without any apn")

	modems, message = __getModemsFromDBus(bus)
	if modems == None:
		logger.info(message)
		return

	try:
		for path, properties in modems:
			if "org.ofono.ConnectionManager" not in properties["Interfaces"]:
				continue

			connman = dbus.Interface(bus.get_object('org.ofono', path), 'org.ofono.ConnectionManager')
			contexts = connman.GetContexts()

			path = ""
			for i, properties in contexts:
				if properties["Type"] == "internet":
					path = i
					break

			if path == "":
				path = connman.AddContext("internet")
				logger.info(("Created new context %s" % (path)))
			else:
				logger.info(("Found context %s" % (path)))

			context = dbus.Interface(bus.get_object('org.ofono', path),	'org.ofono.ConnectionContext')

			if len(apn) > 0:
				context.SetProperty("AccessPointName", apn)
				logger.info(("Setting apn to %s" % (apn)))

			if len(user_name) > 0:
				context.SetProperty("Username", user_name)
				logger.info(("Setting username to %s" % (user_name)))

			if len(password) > 0:
				context.SetProperty("Password", password)
				logger.info(("Setting password to %s" % (password)))

			#Necessary to wait a bit after context creation
			time.sleep(3)
	except dbus.DBusException as e:
		message = "DBus exception while setting internet contexts:%s" % (e)
	except Exception as e:
		message = "Generic exception while setting internet contexts:%s" % (e)

def isInternetContextActive(bus, verbose=False, attempts=1, delay=5):
	return __retryFunction(__isInternetContextActive, bus, verbose, attempts, delay)

def __isInternetContextActive(bus, verbose):
	""" retrieve Internet context status in Ofono (active or not). An active Internet context means ppp0 is mounted
	"""

	if verbose:
		logger.info("")
		logger.info("-Check for Internet context")

	status = False

	modems, message = __getModemsFromDBus(bus)
	if modems != None:
		modem_path = modems[0][0]

		try:
			connection_manager_interface = dbus.Interface(bus.get_object('org.ofono', modem_path),'org.ofono.ConnectionManager')

			# retrieve internet context
			contexts = connection_manager_interface.GetContexts()
			# use first context
			if len(contexts) == 0:
				message = "No Internet context found"

			# ofono.ConnectionContext contains information about ppp connection
			the_context = contexts[0][0]
			connection_context = dbus.Interface(bus.get_object('org.ofono', the_context),'org.ofono.ConnectionContext')
			status = __dbus2py(connection_context.GetProperties()['Active'])
			if status:
				message = "Internet context is active"
			else:
				message = "Internet context is not active"

		except dbus.DBusException as e:
			message = "DBus exception while checking Internet context status:%s" % (e)
		except KeyError as e:
			message = "KeyError exception: %s not present on Dbus" % (e)
		except Exception as e:
			message = "Generic exception while checking Internet context status:%s" % (e)

	if verbose:
		logger.info(message)
	return status, message

def contactServer(verbose=False, attempts=1, delay=5):
	return __retryFunction(__contactServer, None, verbose, attempts, delay)

def __contactServer(verbose=False):
	"""try to establish a connection to a server
	Two reference servers are used; return True if a least one server is reachable
	"""
	status = False
	servers_urls = [ 'storefsngeneral.blob.core.windows.net', 'pool.ntp.org' ]
	count = 0
	message = ""
	for server_url in servers_urls:
		if verbose:
			logger.info("")
			logger.info("-Contact %s" % (server_url))

		if lib_network.contact_server(interface_name=CELLULAR_INTERFACE_NAME, server_urls=[server_url]):
			status = True
			loop_msg = "Contact to %s successful" % (server_url)
		else:
			loop_msg = "Impossible to contact %s"  % (server_url)

		if verbose:
			logger.info(loop_msg)
		if count > 0:
			message += ", "
		message += loop_msg

		# the first successful contact exits the loop
		if status == True:
			break
		else:
			count += 1

	return status, message

def getCellularServiceInConnman(bus, verbose=False, attempts=3, delay=5):
	return __retryFunction(__getCellularServiceInConnman, bus, verbose, attempts, delay)

def __getCellularServiceInConnman(bus, verbose):
	""" Wait until a cellular service is listed by Connman
	"""

	if verbose:
		logger.info("")
		logger.info("-Wait for cellular service creation by ofono, listed in connman...")
	status = False
	try:
		manager = dbus.Interface(bus.get_object("net.connman", "/"), "net.connman.Manager")
		services = manager.GetServices()
		for path, properties in services:
			if path.find("cellular_") != -1:
				status = True
				message = path
				#the service is listed but not really ready to be connected... wait a bit for it
				#this timing differs from one provider to another...
				time.sleep(5)
				break
		if not status:
			message = "No cellular service seen by Connman"
	except dbus.DBusException as e:
		message = "DBus exception while waiting for cellular service in Connman:%s" % (e)
	except Exception as e:
		message = "Generic exception while waiting for cellular service in Connman:%s" % (e)
	if verbose:
		logger.info(message)
	return status, message

def connectToCellularServiceInConnman(bus, cellular_service_path, verbose=False, attempts=2, delay=5):
	"""Connect connman to a cellular service, with retries
	"""
	for attempt in range(0,attempts):
		if attempt > 0:
			time.sleep(delay)
			if verbose:
				logger.info("")
				logger.info("-Attempt #%d->" % (attempt+1))
		status, message = __connectToCellularServiceInConnman(bus, cellular_service_path, verbose)
		if status:
			break	#success, no need to retry anymore
	return status, message

def __connectToCellularServiceInConnman(bus, cellular_service_path, verbose):
	"""Connect connman to a cellular service.
	"""

	if verbose:
		logger.info("")
		logger.info("-Connect to cellular service \"%s\"..." % (cellular_service_path))
	status = False
	try:
		service = dbus.Interface(bus.get_object("net.connman", cellular_service_path), "net.connman.Service")
		service.Connect(timeout=10000)	#ask for connection, use long timeout
		service.SetProperty("AutoConnect", True)	#mandatory: this cellular service will automatically be connected at next startup
		status = True
		message = "Successful connection"
	except dbus.DBusException as e:
		message = "DBus exception while connecting to cellular service in Connman:%s" % (e)
	except Exception as e:
		message = "Generic exception while connecting to cellular service in Connman:%s" % (e)
	if verbose:
		logger.info(message)
	return status, message

def isOfonodRunning():
	"""check if ofono daemon is running, return tuple (status, message)
	"""
	(status, message) = lib_system.isProcessRunning("ofonod")
	return (status, message)


def getProviderMode(bus):
	""" Returns provider mode
		"att"     - AT&T
		"verizon" - Verizon
		"unknown" - Error
	"""

	modems, message = __getModemsFromDBus(bus)
	if modems != None:
		modem_path = modems[0][0]

		try:
			provider = dbus.Interface(bus.get_object('org.ofono', modem_path), 'org.ofono.TelitProvider')
			return "att" if provider.GetProperties()["VerizonMode"] == 0 else "verizon"
		except Exception as e:
			return "unknown"

	return "unknown"

def configureProviderMode(bus, mode, verbose = False):
	""" switches modem to the selected provider/firmware mode
		Supported modes are "verizon" and "att"
	"""

	modems, message = __getModemsFromDBus(bus)
	if modems != None:
		modem_path = modems[0][0]

		try:
			if mode == "verizon":
				fwswitch_config = 1
			elif mode == "att":
				fwswitch_config = 0
			else:
				return False, "Unsupported mode"

			if mode == getProviderMode(bus):
				return True, "Already in the selected mode"

			provider = dbus.Interface(bus.get_object('org.ofono', modem_path), 'org.ofono.TelitProvider')
			provider.SetProperty("VerizonMode", dbus.Boolean(fwswitch_config))
			return True, "Success"
		except dbus.DBusException as e:
			message = "DBus exception while configuring provider mode:%s" % (e)
		except Exception as e:
			message = "Generic exception while configuring provider mode:%s" % (e)

	if verbose:
		logger.info(message)

	return False, message

def isNorthAmericaModemViaDBus(bus):
	"""
	Determine if the first modem seen on DBus is a North America modem.

	Result:
		True:  the first modem found is made for North America cellular networks
		False: the first modem found is not made for North America cellular networks
	"""

	modems, _ = __getModemsFromDBus(bus)
	if modems != None:
		modem_path = modems[0][0]

		try:
			modem = dbus.Interface(bus.get_object('org.ofono', modem_path), 'org.ofono.Modem')
			model = modem.GetProperties()["Model"]
			#LE910-EU for Europe, LE910-NA for North America
			if (type(model) == dbus.String) and ("NA" in model):
				return True
		except Exception as e:
			return False
	return False

def isNorthAmericaModemViaSerial():
	"""
	Determine if the modem connected to serial is a North America modem.
	This function shouldn't be called when some process uses the modem serial
	console (/dev/ttyACM0); i.e. ofono should not be running.

	Result:
		True:  the modem is made for North America cellular networks
		False: the modem is not made for North America cellular networks
	"""

	modem_count, _, _ = listUSBModems(False)
	if modem_count > 0:
		status, answer = sendSerialCommandToModem("AT#FWSWITCH?\r\n")

		if status and "OK" in answer:
			return True

	return False

def configureTechnologyPreference(bus, technologies, verbose = False):
	"""
	Configure what cellular network technologies the modem should use.
	Possible values for the parameter "technologies" are:
	    * "any"     : use any technology supported by the modem (2G, 3G, 4G)
	    * "gsm"     : only use 2G technology
	    * "umts"    : only use 3G technology
	    * "lte"     : only use 4G technology
	    * "gsm-umts": only use 2G or 3G technologies
	    * "gsm-lte" : only use 2G or 4G technologies
	    * "umts-lte": only use 3G or 4G technologies

	This function should be called only when a SIM card is detected in the modem.
	Therefore, one must ensure that this condition fulfilled before calling it.
	"""

	success = False

	modems, message = __getModemsFromDBus(bus)
	if modems != None:
		modem_path = modems[0][0]

		try:
			radiosettings = dbus.Interface(bus.get_object('org.ofono', modem_path), 'org.ofono.RadioSettings')
			radiosettings.SetProperty("TechnologyPreference", technologies);

			message = "Cellular technology preferences set to '%s'" % (technologies)
			success = True
		except dbus.exceptions.DBusException as e:
			if e.get_dbus_name() == "org.ofono.Error.InvalidArguments":
				message = "'%s' is not a valid cellular technology name" % (technologies)
			else:
				message = "DBus error while trying to configure ofono technology preferences: %s" % (e)
		except Exception as e:
			message = "Failed to configure cellular technology preferences: %s" % (e)

	if verbose:
		print(message)

	return success, message
