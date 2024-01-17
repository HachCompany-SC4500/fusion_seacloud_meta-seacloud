#!/usr/bin/python3

import lib_modem
import lib_system
import lib_cellular_stats
import shutil
import os
import time
import dbus
import sys
import logging
import lib_logger

LOGS_FILE_PATH = "/media/persistent/system/config_modem_logs"
LOGS_FILE_MAX_BYTES = 512*1024
LOGS_FILE_BACKUP_COUNT = 1

# Size of logs generated by cellular connection : 20 KBytes
# 512 KBytes --> History of the last 25 attempts to configure cellular

logger = logging.getLogger(__name__)

# North America Multitech modems contain two firmwares. Each of these firmware can handle only one
# of the two cellular technology available in the USA:
#   - firmware "att": can connect to the North America network
#   - firmware "verizon": can connect to the Verizon network
#
# This define the default modem firmware to use for North America modem (it is irrelevant for other modem types).
# If no firmware mode is specified on command line or in configuration, a North America modem will
# be configured to use this firmware by default.
# Possible values are "att" and "verizon".
NA_MODEM_DEFAULT_FW = "att"

# Name of the systemd service responsible of loading modem configuration after an update
MODEM_CONFIG_LOADER_SERVICE = "modem_configuration_loader.service"

def showHelp(script_name):
	logger.info("")
	logger.info("bad or missing argument")
	logger.info("")
	logger.info("use: [PIN] [APN] [Username] [Password] (e.g. \"%s 1234 gprs.swisscom.ch bob dylan\")" % (script_name))
	logger.info("or (North America only)")
	logger.info("use: [PIN] [APN] [Username] [Password] [Network] (e.g. \"%s 1234 gprs.swisscom.ch bob dylan verizon\")" % (script_name))
	logger.info("or")
	logger.info("use: \"%s loadconf\" to load existing configuration from permanent memory" % (sys.argv[0]))
	logger.info("or")
	logger.info("use: \"%s clearconf\" to clear any previous modem configuration" % (sys.argv[0]))
	logger.info("")
	logger.info("or")
	logger.info("use: \"%s enable\" to check if modem is present, if present enable the modem" % (sys.argv[0]))
	logger.info("")
	logger.info("or")
	logger.info("use: \"%s disable\" to clear any previous configuration and disable modem" % (sys.argv[0]))
	logger.info("")
	logger.info("or")
	logger.info("use: \"%s is_enabled\" to check if modem is enable or disable" % (sys.argv[0]))
	logger.info("")
	logger.info("or")
	logger.info("use: \"%s is_modem_present\" to check if a modem is connected to controller (DEPRECATED: use \"get_modem_type\" instead)" % (sys.argv[0]))
	logger.info("")
	logger.info("or")
	logger.info("use: \"%s get_modem_type\" to check if a modem is connected to controller and to get its type (\"us\" or \"eu\")" % (sys.argv[0]))
	logger.info("")
	logger.info("or")
	logger.info("use: \"%s get_configuration\" to return current modem configuration" % (sys.argv[0]))
	logger.info("")

def enableAndStartOfonod():
	logger.info("")
	logger.info("-Enable and start ofono service")
	lib_modem.enableOfonod()
	lib_modem.startOfonod()
	#Wait a bit when starting ofono to let him discovering modems. Ofono is longer to start just after an OS upgrade
	time.sleep(10)

def enableAndStartCellularDataSupervisor():
	""" Enable & start a timer-background service that check connectivity status every X minutes
	"""
	logger.info("")
	logger.info("-Enable and start cellular data supervisor service")
	lib_modem.enableCellularDataSupervisor()
	lib_modem.startCellularDataSupervisor()

	lib_system.sync()

def enableAndStartCellularSignalStrengthMonitor():
	""" Enable & start service that send SignalStrength level to backend over SocketIO
	"""
	logger.info("")
	logger.info("-Enable and start cellular SignalStrength monitor service")
	lib_modem.enableCellularSignalStrengthMonitor()
	lib_modem.startCellularSignalStrengthMonitor()

	lib_system.sync()

def clearConfiguration(remove_config_modem_file = False):
	"""Stops cellular data connectivity. Clear related configuration data
	"""
	logger.info("")
	logger.info("-Stops cellular data connectivity")

	# reset uptime
	lib_cellular_stats.clearUpTime()

	if remove_config_modem_file == True:
		lib_modem.removeConfigModemFile()

	# Stop and disable cellular data supervisor
	lib_modem.stopCellularDataSupervisor()
	lib_modem.disableCellularDataSupervisor()

	# Stop and disable cellular SignalStrength monitor
	lib_modem.stopCellularSignalStrengthMonitor()
	lib_modem.disableCellularSignalStrengthMonitor()

	# Stop and disable ofonod
	lib_modem.stopOfonod()
	lib_modem.disableOfonod()

	# Remove cellular settings in connman (if any)
	connman_settings_folder = "/var/lib/connman/"
	try:
		for f in os.listdir(connman_settings_folder):
			if(f.startswith("cellular_")):
				try:
					shutil.rmtree(connman_settings_folder+f, False, None)
					logger.info("Removed dir %s" % (connman_settings_folder+f))
				except OSError:
					pass
	except Exception as e:
		logger.warning("Failed to clear connman configuration files: {}".format(e))

	# Remove ofono settings (if any)
	ofono_settings_folder = "/var/lib/ofono/"
	try:
		if os.path.exists(ofono_settings_folder):
			shutil.rmtree(ofono_settings_folder, False, None)
			logger.info("Removed dir %s" % (ofono_settings_folder))
	except Exception as e:
		logger.warning("Failed to clear ofono configuration files: {}".format(e))

	lib_system.sync()

def exitInError(modem_diagnostic_code):
	"""Common exit function in case of failures
	"""

	if load_existing_configuration:
		# failed to apply existing modem configuration:
		# - clear configuration and keep modem configuration file for next tentative
		clearConfiguration(False)
	else:
		# failed to apply NEW modem configuration, clear all configuration stuff done so far
		clearConfiguration(True)

	# reboot modem (hard) to be fresh for next configuration (except when several modems are present)
	if modem_diagnostic_code != lib_modem.ModemDiagnosticCode.SeveralModemsArePresent:
		lib_modem.rebootModemHard()

	modem_diagnostic_code_value = modem_diagnostic_code.value

	logger.error("")
	logger.error("---Finishing in Error with code %d---" % (modem_diagnostic_code_value))
	lib_cellular_stats.logModemDiagnostic(modem_diagnostic_code)
	exit(modem_diagnostic_code_value)

def exitInSuccess():
	"""Common exit function in case of success
	"""

	if NA_modem:
		lib_modem.saveConfigModemFile(pin, apn, user_name, password, fwmode, True)
	else:
		lib_modem.saveConfigModemFile(pin, apn, user_name, password, verbose = True)

	logger.info("")
	logger.info("---Configuration successful---")
	lib_cellular_stats.logModemDiagnostic(lib_modem.ModemDiagnosticCode.WellConfigured)

	# Disable the modem configuration loader service as at this point the configuration is saved by ofono
	lib_system.disableService(MODEM_CONFIG_LOADER_SERVICE)

	exit(lib_modem.ModemDiagnosticCode.WellConfigured.value)

# getModemStateFilePath : this file will be created when enable modem is called and removed when disable modem called.
def getModemStateFilePath():
	"""path to the file containing modem configuration file
	"""
	return "/media/persistent/system/modem_state"

#saveModemState : save modem state to refer if modem is enable/disable,
#if file is present on the path it means modem is in enable state else in disable state
def saveModemState():
	my_file = open(getModemStateFilePath(),"w+")
	my_file.close();

# isModemEnabled : when we switch/open page, this function will check if modem is already enabled or not by checking the modem_status file.
def isModemEnabled():
	if os.path.isfile(getModemStateFilePath()):
		return True
	return False

# isModemPresent : check for available connected modem with device
def isModemPresent(verbose=True):
	mounted_modems_count, mounted_modems_message, mounted_modems_list = lib_modem.listUSBModems(verbose)
	if mounted_modems_count >= 1:
		return True
	return False

# disableModem : this function will remove modem_status file to state that modem is in disable state
# Also, if modem is configured, it will remove all the configuration to disable modem.
def disableModem():
	if os.path.isfile(getModemStateFilePath()):
		os.remove(getModemStateFilePath())
	if lib_modem.isModemConfigured():
		clearConfiguration(True)
	return True

if __name__ == '__main__':
	""" Setup and configure Telit modem and its SIM. It mainly deals with connman & ofono but not only.
	It returns a ModemDiagnosticCode(Enum) that reflects the status
	"""

	# Configure root logger to catch logs of the application and of libraries
	tag_name = "config_cellular"
	lib_logger.add_handler_file(tag_name, LOGS_FILE_PATH, LOGS_FILE_MAX_BYTES, LOGS_FILE_BACKUP_COUNT)

	stdout_handler = logging.StreamHandler(sys.stdout)
	stdout_handler.setLevel(logging.INFO)
	logging.getLogger().addHandler(stdout_handler)

	(is_syslog_active, _) = lib_system.isServiceActive(lib_logger.SYSLOGD_SERVICE)
	if is_syslog_active:	# Log to syslog only if syslog service is active to avoid exception messages on the console
		lib_logger.add_handler_syslog(tag_name)

	# Log a header to signal start of configuration
	# Log the command line arguments
	lib_logger.log_header_to_logger(logger, logging.DEBUG, "Cellular configuration start - Log time is in UTC")
	command = ""
	for argument in sys.argv:
		command = command + argument + " "
	logger.debug(command)

	load_existing_configuration = False
	good_usage = False
	if (len(sys.argv) == 1+1):	# 1 argument is given after script name
		if sys.argv[1] == "enable":
			# check for available modem, if modem is present enable it and save the state.
			logger.info("Enable modem")
			if isModemPresent() :
				logger.info("")
				logger.info("Modem enabled successfully")
				saveModemState()
				exit(0)
			logger.error("")
			logger.error("Failed to enable modem")
			exit(lib_modem.ModemDiagnosticCode.ModemIsAbsent.value)
		if sys.argv[1] == "disable":
			logger.info("Disable modem")
			logger.info("")

			# when this argument is given, remove the config file if present and remove the modem_state file.
			disableModem()
			logger.info("Modem is disabled")
			exit(0)
		if sys.argv[1] == "is_enabled":
			#when this argument is given, check if modem_state file is present,
			#if present - modem is in enable state, if not present - modem is in disable state.
			if isModemEnabled():
				logger.info("Modem is enabled")
				exit(0)
			logger.info("Modem is disabled")
			exit(1)
		elif sys.argv[1] == "loadconf":
			# when this argument is given, we try to load modem configuration from the persistent partition
			# Note: fwmode is only used to configure North America modems and ignored for other modem types
			result, pin, apn, user_name, password, fwmode = lib_modem.loadConfigModemFile()

			if result == False:
				exit(1)

			load_existing_configuration = True
			good_usage = True
		elif sys.argv[1] == "clearconf":
			#when this argument is given, we clear  any previous modem configuration
			clearConfiguration(True)
			exit(0)
		elif sys.argv[1] == "is_modem_present":
			# Warning: this is deprecated and will be removed in the next release. Please use "get_modem_type" instead
			#when this argument is given, we check if any modem is connected to the system
			if isModemPresent(False):
				logger.info("Modem is present")
				exit(0)
			logger.info("Modem is absent")
			exit(1)
		elif sys.argv[1] == "get_modem_type":
			if isModemPresent(False):
				logger.info("Modem is present")

				NA_modem = False

				ofono_running, _ = lib_modem.isOfonodRunning()
				if ofono_running:
					the_bus = dbus.SystemBus()
					NA_modem = lib_modem.isNorthAmericaModemViaDBus(the_bus)
				else:
					NA_modem = lib_modem.isNorthAmericaModemViaSerial()

				modem_type = "us" if NA_modem else "eu"
				logger.info(modem_type)
				exit(0)
			else:
				logger.info("Modem is absent")
				exit(1)
		elif sys.argv[1] == "get_configuration":
			#when this argument is given, we check modem is currently configured and return current configuration
			if lib_modem.isModemConfigured() == False:
				logger.info('Modem is not configured')
				exit(1)
			logger.info('Modem is configured')
			result, pin, apn, user_name, password, fwmode = lib_modem.loadConfigModemFile(False)
			logger.info(pin)
			logger.info(apn)
			logger.info(user_name)
			logger.info(password)

			# This should display a line only in the presence of a North America modem
			if fwmode != "":
				logger.info(fwmode)

			exit(0)
	elif len(sys.argv) == 4+1 or len(sys.argv) == 5+1:	# 4 or 5 arguments are given after script name
		# The first 4 arguments are always: PIN, APN, Username and Password
		pin = sys.argv[1]
		apn = sys.argv[2]
		user_name = sys.argv[3]
		password = sys.argv[4]

		# An optional fifth argument can set the modem firmware mode ("att" or "verizon") of a North America modem (it is ignored for other modem types)
		if len(sys.argv) == 5+1:
			fwmode = sys.argv[5]
		else:
			fwmode = NA_MODEM_DEFAULT_FW

		good_usage = True
	if not good_usage:
		#Bad or missing argument, show the help
		showHelp(sys.argv[0])
		exit(1)

	logger.info("PIN: \"%s\"" % (pin))
	logger.info("APN: \"%s\"" % (apn))
	logger.info("Username: \"%s\"" % (user_name))
	logger.info("password: \"%s\"" % (password))

	# if modem is enabled through command prompt, save the modem status for UX mode.
	saveModemState()

	if load_existing_configuration:
		# Clear current configuration (if any) but keep any existing modem configuration file for any further tentative
		clearConfiguration(False)
	else:
		# Stops cellular data connectivity. Clear all related configuration data as it is a new configuration request
		clearConfiguration(True)

	# look for a compatible modem on the system.
	# prevent customer from using several modems
	mounted_modems_count, mounted_modems_message, mounted_modems_list = lib_modem.listUSBModems(True)
	if mounted_modems_count == 0:
		exitInError(lib_modem.ModemDiagnosticCode.ModemIsAbsent)
	elif mounted_modems_count > 1:
		exitInError(lib_modem.ModemDiagnosticCode.SeveralModemsArePresent)

	# Log a set of information from modem for diagnostic purpose
	lib_modem.logModemDiagnosticInformation()

	enableAndStartOfonod()

	logger.info("")
	logger.info("-Check if ofonod process is running")
	status, message = lib_modem.isOfonodRunning()
	logger.info(message)
	if not status:
		exitInError(lib_modem.ModemDiagnosticCode.OfonodNotRunning)

	# Get DBus
	the_bus = dbus.SystemBus()

	status, message = lib_modem.isModemOnDBus(the_bus, True, 5)
	if not status:
		exitInError(lib_modem.ModemDiagnosticCode.ModemIsNotRecognized)

	# List the content of all information related to modems on DBus
	# This enumeration can be instantanous when empty or partially discovered by ofono.
	# Force a minimum duration of 1 minute
	# Necessary to wait for more interfaces (especially simManager and networkRegistration) that are used right after this listing
	start = time.time()
	lib_modem.enumerateModems(the_bus)
	end = time.time()
	duration = end - start
	if duration < 60:
		wait_duration = round(60-duration, 0)
		logger.info("-Sleep for %s s" % (wait_duration))
		time.sleep(wait_duration)

	# Determining if the current modem seen on DBus is made for the North America network.
	NA_modem = lib_modem.isNorthAmericaModemViaDBus(the_bus)

	# As opposed to European modems, North America ones carry two different firmwares ("att" or "verizon"). Therefore,
	# testing if a modem is made for the North America network is necessary before handling
	# its firmwares.

	# Setting the modem firmware for North America modem
	logger.info("")
	if NA_modem:
		logger.info("This is North America modem")
		current_firmware = lib_modem.getProviderMode(the_bus)
		logger.info("North America modem firmware mode currently enabled: '%s'" % (current_firmware))

		if fwmode != current_firmware:
			logger.info("Switching the North America modem firmware to: '%s'" % (fwmode))
			status, message = lib_modem.configureProviderMode(the_bus, fwmode, verbose = True)
			if not status:
				exitInError(lib_modem.ModemDiagnosticCode.SwitchFirmwareFailed)

			# After a firmware switch, the modem reboots automatically.
			# It usually takes less than 15 seconds to reboot, so we wait 30 seconds
			# to have some buffer time.
			time.sleep(30)

			os.execv(sys.argv[0], sys.argv)
	else:
		logger.info("This is European modem")

	status, message = lib_modem.isSimPresent(the_bus, True, 5)
	if not status:
		exitInError(lib_modem.ModemDiagnosticCode.SimIsAbsent)

	# Retrieve Pin status and ask pin if required
	status, message = lib_modem.getPinStatus(the_bus, True)
	if status == lib_modem.PinStatus.Unknown:
		exitInError(lib_modem.ModemDiagnosticCode.SimError)
	elif status == lib_modem.PinStatus.PukIsRequired:
		exitInError(lib_modem.ModemDiagnosticCode.SimIsPukLocked)

	if status == lib_modem.PinStatus.PinIsRequired:
		if len(pin) == 0:
			exitInError(lib_modem.ModemDiagnosticCode.SimIsPinLocked)	#Sim is locked but no PIN is given
		else:
			status, message = lib_modem.disablePin(the_bus, pin, True)
			if status == lib_modem.DisablePinAnswer.Unknown:
				exitInError(lib_modem.ModemDiagnosticCode.SimError)
			elif status == lib_modem.DisablePinAnswer.WrongPin:
				exitInError(lib_modem.ModemDiagnosticCode.SimIsPinLocked)

	# retrieve service provider name, displayed for information purpose
	# may need a couple of seconds to be available after PIN unlocking
	provider_name, dummy_msg = lib_modem.getServiceProviderName(the_bus, True, 5)

	# Telenor SIM cards are provided with controllers and are supposed to be used in multiple countries.
	# Roaming is necessary when using SIM card linked to a mobile provider based in a different country
	# than the one the SIM card is used in.
	# Historically, roaming was enabled exactly below this comment, but it proved to be too late.
	# Even enabling roaming right after starting ofono in this scrict was still to late.
	# Therefore, our version of Ofono has been patched to allow roaming by default.

	# wait for network registration
	status, message = lib_modem.isCellularNetworkRegistered(the_bus, True, 10)
	if not status:
		exitInError(lib_modem.ModemDiagnosticCode.NetworkIsUnregistered)

	status, message = lib_modem.isDataNetworkRegistered(the_bus, True, 20)
	if not status:
		exitInError(lib_modem.ModemDiagnosticCode.GPRSNetworkNotRegistered)

	# clear any internet context in the Sim to force creation of a new one
	lib_modem.clearInternetContext(the_bus)
	lib_modem.setInternetContext(the_bus, apn, user_name, password)

	status, cellular_service_path = lib_modem.getCellularServiceInConnman(the_bus, True, 3)
	# even if cellular service is listed on connman, it does NOT mean that apn settings are valid
	if not status:
		exitInError(lib_modem.ModemDiagnosticCode.APNConnectionFailed)

	# The cellular service is now ready to be connected via connman
	status, message = lib_modem.connectToCellularServiceInConnman(the_bus, cellular_service_path, True)
	# the connection fails when in case of wrong apn (DBus exception while connecting to cellular service in Connman:net.connman.Error.Failed: Input/output error)
	if not status:
		exitInError(lib_modem.ModemDiagnosticCode.APNConnectionFailed)

	status, message = lib_modem.isInternetContextActive(the_bus, True, 3)
	if not status:
		exitInError(lib_modem.ModemDiagnosticCode.InternetContextFailed)

	enableAndStartCellularDataSupervisor()
	enableAndStartCellularSignalStrengthMonitor()

	exitInSuccess()
