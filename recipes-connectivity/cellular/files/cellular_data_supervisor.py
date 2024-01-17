#!/usr/bin/python3

import lib_modem
import lib_cellular_stats
import dbus
import threading
import sys
import time
import subprocess
import logging

def getModemDiagnostic(bus):
	""" Check cellular connectivity and returns whole modem diagnostic in case of failure, return tuple (status, message)
	"""

	# To check cellular connectivity: read Internet Context status on DBus + contact a server
	# several attempts
	signal_strength = -1
	tech = 'none'
	status, internet_context_message = lib_modem.isInternetContextActive(bus, False, 3)
	if status:
		# get signal strenght and technology
		modem_on_dbus, message = lib_modem.isModemOnDBus(bus)
		if modem_on_dbus:
			signal_strength, message, tech = lib_modem.getSignalStrength(bus)
		# get connectivity
		status, message =  lib_modem.contactServer(False, 3)
		if status:
			return lib_modem.ModemDiagnosticCode.WellConfigured, internet_context_message + ", " + message, signal_strength, tech

	# At this stage, the cellular connectivity is identified as faulty
	# So we build here a detailed diagnostic, step by step
	full_message = ""
	mounted_modems_count, mounted_modems_message, mounted_modems_list = lib_modem.listUSBModems(False)
	full_message += mounted_modems_message
	if mounted_modems_count == 0:
		return lib_modem.ModemDiagnosticCode.ModemIsAbsent, full_message, signal_strength, tech
	elif mounted_modems_count > 1:
		return lib_modem.ModemDiagnosticCode.SeveralModemsArePresent, full_message, signal_strength, tech

	status, message = lib_modem.isOfonodRunning()
	full_message += ", %s" % (message)
	if not status:
		return lib_modem.ModemDiagnosticCode.OfonodNotRunning, full_message, signal_strength, tech

	status, message = lib_modem.isModemOnDBus(bus)
	full_message += ", %s" % (message)
	if not status:
		return  lib_modem.ModemDiagnosticCode.ModemIsNotRecognized, full_message, signal_strength, tech

	status, message = lib_modem.isSimPresent(bus)
	full_message += ", %s" % (message)
	if not status:
		return  lib_modem.ModemDiagnosticCode.SimIsAbsent, full_message, signal_strength, tech

	status, message = lib_modem.getPinStatus(bus)
	full_message += ", %s" % (message)
	if status == lib_modem.PinStatus.Unknown:
		return lib_modem.ModemDiagnosticCode.SimError, full_message, signal_strength, tech
	elif status == lib_modem.PinStatus.PukIsRequired:
		return lib_modem.ModemDiagnosticCode.SimIsPukLocked, full_message, signal_strength, tech
	elif status == lib_modem.PinStatus.PinIsRequired:
		return lib_modem.ModemDiagnosticCode.SimIsPinLocked, full_message, signal_strength, tech

	status, message = lib_modem.isCellularNetworkRegistered(bus)
	full_message += ", %s" % (message)
	if not status:
		return lib_modem.ModemDiagnosticCode.NetworkIsUnregistered, full_message, signal_strength, tech

	status, message = lib_modem.isDataNetworkRegistered(bus)
	full_message += ", %s" % (message)
	if not status:
		return lib_modem.ModemDiagnosticCode.GPRSNetworkNotRegistered, full_message, signal_strength, tech

	status, message = lib_modem.isInternetContextActive(bus)
	full_message += ", %s" % (message)
	if not status:
		return lib_modem.ModemDiagnosticCode.APNConnectionFailed, full_message, signal_strength, tech

	status, message =  lib_modem.contactServer(False, 3)
	full_message += ", %s" % (message)
	if not status:
		return lib_modem.ModemDiagnosticCode.ContactServerFailed, full_message, signal_strength, tech

	return lib_modem.ModemDiagnosticCode.WellConfigured, message, signal_strength, tech

failure_counter_path = "/tmp/cellular_data_supervisor_failure_counter"
def getFailureCounter():
	"""read the current number of failures since the last reboot
	"""
	try:
		with open(failure_counter_path, 'r') as failure_counter_file:
			failure_counter = failure_counter_file.read()
		failure_counter = int(failure_counter)
	except Exception as e:
		# no failure_counter_file after reboot (/tmp is volatile)
		return 0
	return failure_counter

def incrementFailureCounter():
	"""increment the number of failures since the last reboot
	"""
	try:
		failure_counter = str(getFailureCounter()+1)
		with open(failure_counter_path, 'w') as failure_counter_file:
			failure_counter_file.write(failure_counter)
	except Exception as e:
		return
	return

def displayFailureCounter():
	"""it prints the current number of failures since the last reboot
	"""
	logger.info("Total number of failures since last reboot %d" % (getFailureCounter()))


def displayUptimeCounter():
	logger.info("Connection uptime (hh.mm) %.2f" % lib_cellular_stats.computeUpTime())

if __name__ == '__main__':
	"""This Python script aims at correcting the bug "CYSCAT-88 3G: If the controller lost the 3G connection, he failed to reconnect by itself to the 3G"

	After an initial successful modem configuration (see set_config_modem.py), it is launched every X minutes by systemctl. (see cellular_data_supervisor.service and cellular_data_supervisor.timer in /etc/systemd/system)

	By consequence, it is not active in case LAN/Ethernet connection

	It checks and logs the validity of the cellular data connection (=Internet via GPRS/3G/4G). It mainly bases its diagnostic on Dbus values written by Ofonod and also on some extra sources
	-In case of a working cellular data connexion, this program simply logs the positive result and exits (and will be run again X minutes later)
	-In case of a faulty cellular data connection, it logs a detailed diagnostic of the failure/root cause (modem, driver, Ofono, SIM, etc) and applies the adapted corrective action to recover (resetting the modem, restarting ofono etc) and exits.

	An optional command line argument "diagonly" is supported. In this case, this program will stop after displaying the cellular data connection diagnostic and will not take any corrective action to recover from any issue.
	With "stats" argument, the program will stop after displaying uptime counter and failure counter
	"""

	logging.getLogger().setLevel(logging.INFO)

	# Redirect logging messages to stdout
	logger = logging.getLogger(__name__)
	logger.addHandler(logging.StreamHandler(sys.stdout))

	logger_lib_modem = logging.getLogger('lib_modem')
	logger_lib_modem.handlers = logger.handlers

	logger_lib_cellular_stats = logging.getLogger('lib_cellular_stats')
	logger_lib_cellular_stats.handlers = logger.handlers

        # this program can receive one optional argument
	diagnostic_only = False
	if len(sys.argv) > 1:
		# diagonly option: this program will stop after displaying the cellular data connection diagnostic and code (no action to recover from any issue)
		if sys.argv[1] == "diagonly":
			diagnostic_only = True
		# stats option: this program will stop after displaying uptime counter and failure counter
		elif sys.argv[1] == "stats":
			displayUptimeCounter()
			displayFailureCounter()
			exit(0)
		else:
			logger.info("")
			logger.info("bad argument")
			logger.info("")
			logger.info("use: \"%s diagonly\" to display the cellular data connection diagnostic" % (sys.argv[0]))
			logger.info("or")
			logger.info("use: \"%s stats\" to display uptime counter and failure counter" % (sys.argv[0]))
			logger.info("")
			exit(1)

	# Get DBus
	the_bus = dbus.SystemBus()

	# retrieve the full modem diagnostic
	modem_diagnostic, modem_diagnostic_message, signal_strength_value, technology = getModemDiagnostic(the_bus)

	# log the modem diagnostic in stats file
	if not diagnostic_only:
		lib_cellular_stats.logModemDiagnostic(modem_diagnostic, signal_strength=signal_strength_value, tech=technology)

	# log the modem diagnostic and message in journalctl
	if modem_diagnostic == lib_modem.ModemDiagnosticCode.WellConfigured:
		# best case, all is fine about this modem and about the cellular data connection
		logger.info("Cellular data connection is available: %s" % (modem_diagnostic_message))
		if not diagnostic_only:
			displayUptimeCounter()
			displayFailureCounter()
		# sucessful exit code
		exit(lib_modem.ModemDiagnosticCode.WellConfigured.value)
	else:
		# an issue with this modem or cellular data connection
		logger.warning("Cellular data connection is not available: %s (code %d)" % (modem_diagnostic_message, modem_diagnostic.value))

		# this program exits here in case of "diagnostic" only
		# it returns a diagnostic failure code
		if diagnostic_only:
			exit(modem_diagnostic.value)

		# increment volatile failure counter (displayed for statistics purpose)
		incrementFailureCounter()
		displayFailureCounter()

		# The goal is to act on the faulty modem, try to localize it
		mounted_modems_count, mounted_modems_message, mounted_modems_list = lib_modem.listUSBModems(False)

		if mounted_modems_count > 1:
			# Several USB modems detected
			logger.error(mounted_modems_message + ". Nothing we can do to recover...")
		else:
			# The action taken depends on the issue
			action_number = 1

			logger.warning("Step %d: stop Ofonod" % (action_number))
			stop_ofonod_result, stop_ofonod_message = lib_modem.stopOfonod()
			logger.warning("%s" % (stop_ofonod_message))
			time.sleep(4)

			action_number+=1
			logger.warning("Step %d: restart Connman" % (action_number))
			restart_connman_result, restart_connman_message = lib_modem.restartConnman()
			logger.warning("%s" % (restart_connman_message))
			time.sleep(4)

			logger.warning("Step %d: reboot modem (hard)" % (action_number))

			# keep a trace of this forced reboot in stats
			lib_cellular_stats.logForcedModemReboot()

			reboot_modem_result, reboot_modem_message = lib_modem.rebootModemHard()
			logger.warning(reboot_modem_message)

			logger.warning("Last action: start Ofonod again")
			start_ofonod_result, start_ofonod_message = lib_modem.startOfonod()
			logger.warning("%s" % (start_ofonod_message))

	exit(0)
