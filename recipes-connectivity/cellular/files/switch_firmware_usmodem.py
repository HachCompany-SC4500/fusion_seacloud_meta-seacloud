#!/usr/bin/python3
#
# This is a helper script to switch the firmware of a North America modem.
# A North America modem must be connected to the controller to use this script.
# It must be used as followed: switch_firmware_usmodem.py <fwmode>
#     with fwmode being "att" or "verizon".

import sys
import time
import dbus
import lib_modem

if __name__ == '__main__':
	the_bus = dbus.SystemBus()

	try:
		fwmode = sys.argv[1]
	except:
		print("Error: missing argument. Firmware mode to switch to must be provided.", file = sys.stderr)
		print("Example: '%s verizon'" % (sys.argv[0]), file = sys.stderr)
		exit(1)

	NA_modem = lib_modem.isNorthAmericaModem()
	if not NA_modem:
		print("Error: firmware switching is only available for North America modems", file = sys.stderr)
		exit(lib_modem.ModemDiagnosticCode.ModemIsAbsent.value)
	else:
		lib_modem.startOfonod()
		time.sleep(20)
		status, message = lib_modem.configureProviderMode(the_bus, fwmode)
		lib_modem.stopOfonod()

		if not status:
			print("Could not switch North America firmware mode, error: %s" % (message), file = sys.stderr)
			exit(lib_modem.ModemDiagnosticCode.SwitchFirmwareFailed.value)

		print("North America modem firmware switched to '%s'" % (fwmode))
