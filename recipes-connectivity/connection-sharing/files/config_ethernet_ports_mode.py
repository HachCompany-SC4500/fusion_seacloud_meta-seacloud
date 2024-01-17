#!/usr/bin/python3
import subprocess
import sys
import os
import json
import re

ETHERNET_PORTS_MODE_FILE = "/media/persistent/system/ethernet_ports_mode"

CONFIG_SHARENET_SCRIPT = "config_sharenet.py"

SUPPORTED_MODES = ["none", "chain", "split", "mixIEP", "IEPOnly"]

PROFINET_REGEX = "HL001_53251_[0-9a-fA-F]{12}"
ETHERNETIP_REGEX = "HL001_53252_[0-9a-fA-F]{12}"
INDUSTRIAL_ETHERNET_SLOT = 11
FC_ENABLE_PORT2 = 25
FC_DISABLE_PORT2 = 20
REG_PORT2_STATUS = 2 	# Modbus register 40003
PORT2_ENABLED =1
PORT2_DISABLED = 0


def usage(goodargs = False):
	"""
	Print a help message and exit.

	It exits with an non-zero value if goodargs is not set to True, signaling an error.
	"""

	out = sys.stdout if goodargs else sys.stderr

	print("""\
Configure ethernet ports mode

Parameters:
{0} get: return current ethernet ports mode
{0} set <args>:
	with "args" being:
		{1} : no ethernet port
		{2} : two ethernet ports bridged together by main board in order to chain controllers in a the network
		{3} : two ethernet ports used separately by the main board
		{4} : two ethernet ports used separately: one by the main board, second by IEP extension board
		{5} : two ethernet ports bridged together by IEP extension board in order to chain controllers in IEP protocols
{0} update IEP module:
	Read the ethernet ports state saved on the persistent partition and send it to IEP module, if connected.
	This is intended to be run at controller start up to ensure IEP module settings matches the actual saved
	settings, in case of module replacement.
{0} help:
	print this usage guideline

Examples:
{0} get
	print the current ethernet ports mode
{0} set chain
	configure two ethernet ports bridged together by main board
{0} update IEP module
	load and send the configuration saved on the persistent partition to the IEP module (useful in case of module replacement)
""".format(sys.argv[0], SUPPORTED_MODES[0], SUPPORTED_MODES[1], SUPPORTED_MODES[2], SUPPORTED_MODES[3], SUPPORTED_MODES[4]), end="", file=out)

	exit(0 if goodargs else 1)

def read_configuration_file():
	"""
	read configuration file from the persistent partition.
	"""
	try:
		if not os.path.exists(ETHERNET_PORTS_MODE_FILE):
			raise Exception("error, configuration file {} does not exist".format(ETHERNET_PORTS_MODE_FILE))

		with open(ETHERNET_PORTS_MODE_FILE, "r") as config_file:
			configuration = config_file.readline()
		# Remove trailing and leading newlines
		configuration = configuration.strip()
		# detect invalid file content
		if configuration not in SUPPORTED_MODES:
			return False, "Error: invalid configuration '{}' red from file : {}".format(configuration, ETHERNET_PORTS_MODE_FILE)
		return True, configuration
	except Exception as ex:
		return False, "Error: failed to read configuration file from '{}': {}".format(ETHERNET_PORTS_MODE_FILE, ex)

def save_configuration_file(configuration = ""):
	"""
	save configuration file to the persistent partition.
	"""
	try:
		with open(ETHERNET_PORTS_MODE_FILE, "w") as config_file:
			config_file.write(configuration)
		return True, "Configuration saved"
	except Exception as ex:
		return False, "Error: failed to save configuration to '{}': {}".format(ETHERNET_PORTS_MODE_FILE, ex)

def send_configuration_to_IEP_module(mode):
	"""
	send the ethernet port 2 mode configuration to IEP module, if connected
	"""
	try:
		message="No IEP module connected"
		# Check if a Profinet or EtherNetIP module is connected
		command = ["/bin/sh","-c", "TestClientII -d -h{} | grep fusion_id | grep -E -w '{}|{}'".format(INDUSTRIAL_ETHERNET_SLOT,PROFINET_REGEX,ETHERNETIP_REGEX)]
		return_code = subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		if return_code == 0:
			# Profinet or EtherNet/IP module detected. Enable/Disable port 2
			if "IEPOnly" in mode:
				function_code = FC_ENABLE_PORT2
				expected_register_value = PORT2_ENABLED
			else:
				function_code = FC_DISABLE_PORT2
				expected_register_value = PORT2_DISABLED
			command = ["/bin/sh","-c", "TestClientII -h{} -F{}".format(INDUSTRIAL_ETHERNET_SLOT, function_code)]
			subprocess.check_call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

			# Read port 2 status register and parse output to validate setting
			command = ["/bin/sh","-c", "TestClientII -h{} -p -x{}".format(INDUSTRIAL_ETHERNET_SLOT,REG_PORT2_STATUS)]
			output = subprocess.check_output(command, stderr=subprocess.STDOUT).decode()
			output = output.replace("\n","")
			reg_info = re.search("reg +[0-9]+ *: *0x[0-9a-fA-F]+",output)
			if (output.find("failed with") != -1) or not reg_info:
				raise Exception("unable to read IEP module port 2 status reg")
			reg_value = int(reg_info.group(0).split("0x")[1],16)
			if reg_value != expected_register_value:
				raise Exception("unable to write IEP module port 2")

			message="Configuration sent to IEP module"

	except Exception as ex:
		return False, "Exception while sending configuration to IEP module:%s" % (ex)

	return True, message

def get_ethernet_ports_mode():
	# read mode from persistent partition
	status, mode = read_configuration_file()

	# there is not detection of any inconsistency with system configuration here
	# inconsistency can only happen when developper acts directly on system (using CONFIG_SHARENET_SCRIPT directly for example)

	# when nothing has been previously selected, the returned configuration in "none"
	if not status:
		return True, SUPPORTED_MODES[0]

	return True, mode

def set_ethernet_ports_mode(mode):
	# apply mode in system (calling a dedicated system script, see its help for further details)
	# when "chain" is selected, both interfaces fec0 and fec1 are bridged together and are accessible via br0,
	# in other cases only fec1 is accessible via br0

	command = [CONFIG_SHARENET_SCRIPT, 'set', 'bridge', 'fec1']
	if mode == "chain":
		command.append('fec0')

	try:
		with open(os.devnull, 'w') as shutup:
			subprocess.check_call(command, stdout=shutup, stderr=shutup)

		# Send the configuration to the IEP module, if connected
		status, message = send_configuration_to_IEP_module(mode)
		if not status:
			return False, message

	except Exception as ex:
		return False, "exception while configuring ports in system:%s" % (ex)

	# save mode in persistent partition
	return save_configuration_file(mode)

def send_actual_configuration_to_IEP_module():
	"""
	Load configuration saved on the persistent partition and send it to the IEP module.
	This is needed in case of module replacement to ensure that the module matches the actual saved settings.
	"""
	status, mode = get_ethernet_ports_mode()
	return send_configuration_to_IEP_module(mode)

if __name__ == '__main__':
	try:
		if sys.argv[1] == "get":
			status, mode = get_ethernet_ports_mode()
			print(json.dumps({"ethernetPortsMode": mode }, indent = 4))
			if not status:
				exit(1)
			exit(0)
		elif sys.argv[1] == "set" and sys.argv[2] in SUPPORTED_MODES:
			status, message = set_ethernet_ports_mode(sys.argv[2])
			print(message)
			if not status:
				exit(1)
			exit(0)
		elif sys.argv[1] == "update" and sys.argv[2] == "IEP" and sys.argv[3] == "module":
			status, message = send_actual_configuration_to_IEP_module()
			print(message)
			if not status:
				exit(1)
			exit(0)
		elif sys.argv[1] == "help":
			usage(True)
		else:
			usage()
	except IndexError:
		print("{}: error: missing arguments, see help below\n".format(sys.argv[0]), file=sys.stderr)
		usage()
	except Exception as ex:
		print("{}: error: {}".format(sys.argv[0], ex), file=sys.stderr)
		exit(1)
