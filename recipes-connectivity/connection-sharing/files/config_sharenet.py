#!/usr/bin/python3

import configparser
import dbus
import ipaddress
import json
import os
import re
import sys

import lib_network
import lib_system

SYSTEMD_CONFIG_DIR  = "/etc/systemd"
NETWORK_CONFIG_PATH = "/network/br0"
NETWORK_CONFIG_FILE = SYSTEMD_CONFIG_DIR + NETWORK_CONFIG_PATH + ".network"
BRIDGED_CONFIG_PATH = "/network/bridged"
BRIDGED_CONFIG_FILE = SYSTEMD_CONFIG_DIR + BRIDGED_CONFIG_PATH + ".network"

PERSISTENT_CONFIG_BASE = "/media/persistent/system/sharenet"
PERSISTENT_BRIDGED     = PERSISTENT_CONFIG_BASE + "/bridged"
PERSISTENT_TETHERING   = PERSISTENT_CONFIG_BASE + "/tethering"
PERSISTENT_LANSERVER   = PERSISTENT_CONFIG_BASE + "/lanserver"

CONFIGURATION_LOADER = "sharenet_configuration_loader.service"

def usage(goodargs = False):
	"""
	Print a help message and exit.

	It exits with an non-zero value if goodargs is not set to True, signaling an error.
	"""

	out = sys.stdout if goodargs else sys.stderr

	print("""\
Configure connection sharing and tethering feature

Parameters:
{0} get <bridge|tethering|lanserver>:
	bridge:    return the list of currently bridged interface
	tethering: return the current tethering mode
	lanserver: return the LAN server state
{0} set <bridge|tethermode|lanserver> <args>:
	with "args" being:
		bridge:    list of the network interfaces to be bridged, interfaces must be space separated
		tethering: set the tethering mode to use, possible values are
			"cellular": turn on tethering from cellular
			"none":     turn off tethering
		lanserver:
			"yes": turn on the LAN server
			"no":  turn off the LAN server
{0} load <config|configuration>:
	Read the connection sharing state saved on the persistent partition and reapply the saved settings.
	This is intended to be run after a system update, that reverts the settings on the root filesystem
	to their default values.
	"config" and "configuration" values are equivalent.
{0} help:
	print this usage guideline

Examples:
{0} get bridge
	print the list of bridged network interface
{0} set bridge fec0 fec1
	configure the fec0 and fec1 network interfaces to be bridged
{0} set tethering none
	disable tethering
{0} set lanserver yes
	enable the LAN server
{0} load config
	load and apply the configuration saved on the persistent partition (useful after a system update)
""".format(sys.argv[0]), end="", file=out)

	exit(0 if goodargs else 1)

def reload_iptables_rules():
	"""
	Reload IPTables rules for IPv4 and IPv6 to allow network traffic for specific features (e.g. the LAN server).
	"""

	success, _ = lib_system.restartService("iptables.service")
	if not success:
		print("{}: error: failed to reload IPTables rules for IPv4; some network features might not work properly: {}".format(sys.argv[0], ex), file=sys.stderr)

	success, _ = lib_system.restartService("ip6tables.service")
	if not success:
		print("{}: error: failed to reload IPTables rules for IPv6; some network features might not work properly: {}".format(sys.argv[0], ex), file=sys.stderr)

def disable_configuration_loader():
	"""
	Disable the systemd service that is used to reload the configuration saved
	on the persistent partition after an update.
	"""

	success, message = lib_system.disableService(CONFIGURATION_LOADER)
	if not success:
		print("{}: error: {}".format(sys.argv[0], message), file=sys.stderr)

def save_configuration(path, value = ""):
	"""
	Helper to save configuration on the persistent partition.
	The parameter defaults to the empty string to allow creating file flags (i.e. only their existence matters) easily.
	"""

	try:
		dir = os.path.dirname(path)
		if not os.path.exists(dir):
			os.makedirs(dir)

		with open(path, "w") as config_file:
			if value != "":
				config_file.write(value)
	except Exception as ex:
		print("{}: error: failed to save configuration into '{}': {}".format(sys.argv[0], path, ex), file=sys.stderr)

def bridged_interfaces():
	"""
	Return the list of bridged network interfaces.

	The return values is an array possibly containing the following values:
	  * "fec0"
	  * "fec1"
	"""

	bridged = []

	try:
		sysbus = dbus.SystemBus()
		br0_iface = sysbus.get_object("org.freedesktop.network1", "/org/freedesktop/network1" + BRIDGED_CONFIG_PATH)
		bridged = br0_iface.Get("org.freedesktop.network1.Network", "MatchName", dbus_interface = "org.freedesktop.DBus.Properties")

		# "!*" is not an interface name but a wildcard used to allow the bridge to not be linked to any network interface.
		# When used, it is listed in the systemd-networkd DBus answer, so it is removed here.
		if "!*" in bridged:
			bridged.remove("!*")

	except Exception as ex:
		print("{}: error: cannot get the list of bridged interfaces: {}".format(sys.argv[0], ex), file=sys.stderr)

	return bridged

def configure_bridge(if_list, restart_network = False):
	"""
	Configure all listed interface to be bridged together.

	if_list must be a list of network interface(s) specified by name.
	Examples:
	  * ["fec0", "fec1"]: bridge both "fec0" and "fec1" network interfaces
	  * ["fec0"]:         only bridge the "fec0" network interface; this effectively doesn't bridge anything

	Parameter @restart_network determine if systemd-networkd must be restarted
	once the configuration is modified. This allows to apply the new setup
	immediately. This is False by default to avoid restarting systemd-networkd
	multiple times when loading the configuration from the persistent partition.
	"""

	try:
		bridge_config = lib_system.systemd_configparser()

		with open(BRIDGED_CONFIG_FILE, "r") as bridge_file:
			bridge_config.read_file(bridge_file)

		# In case no network interface is provided, "!*" is used. It means not (!) everything (*).
		# This allows to configure the bridge to have no linked network interface linked to it; if the empty string
		# is used here, systemd-networkd links all network interfaces that it can to the bridge.
		bridge_config['Match']['Name'] = " ".join(if_list) if len(if_list) != 0 else "!*"

		with open(BRIDGED_CONFIG_FILE, "w") as bridge_file:
			bridge_config.write(bridge_file, space_around_delimiters = False)

		save_configuration(PERSISTENT_BRIDGED, bridge_config['Match']['Name'])
	except Exception as ex:
		print("{}: error: could not configure the network bridge: {}".format(sys.argv[0], ex), file=sys.stderr)
	
	if restart_network:
		lib_network.restart_systemd_networkd()

def tethering_mode():
	"""
	Return the configured tethering mode.

	Possible return values are:
	  * "cellular": cellular tethering is enabled
	  * "none":     tethering is disabled
	"""

	mode = "none"
	try:
		net_config = lib_system.systemd_configparser()

		with open(NETWORK_CONFIG_FILE, "r") as net_file:
			net_config.read_file(net_file)

		masqurade = net_config['Network']['IPMasquerade']
		if masqurade.lower() == "yes" or masqurade.lower() == "true" or masqurade.lower() == "on" or masqurade == "1":
			mode = "cellular"
	except Exception as ex:
		print("{}: error: could not read tethering current configuration: {}".format(sys.argv[0], ex), file=sys.stderr)

	return mode

def configure_tethering(mode, restart_network = False):
	"""
	Set tethering to the specified mode.

	Valid modes are:
	  * "cellular": enable tethering from cellular network
	  * "none":     disable tethering

	Parameter @restart_network determine if systemd-networkd must be restarted
	once the configuration is modified. This allows to apply the new setup
	immediately. This is False by default to avoid restarting systemd-networkd
	multiple times when loading the configuration from the persistent partition.
	"""

	try:
		net_config = lib_system.systemd_configparser()
		# when cellular requires to first call configure_lanserver before write tethering changes
		if mode == "cellular":
			configure_lanserver(True, permanent = False)

		with open(NETWORK_CONFIG_FILE, "r") as net_file:
			net_config.read_file(net_file)

		if mode == "none":
			net_config['Network']['IPMasquerade'] = "no"
			net_config.remove_option('DHCPServer', 'DNS')

			if os.path.exists(PERSISTENT_TETHERING):
				os.remove(PERSISTENT_TETHERING)
		else:
			# Read and check the controller's configured static IP address
			# on the network interface on which network tethering is enabled.
			# This address will be advertised as the DNS server to use to other devices
			# so that the tethering one can resolve DNS requests for them.
			dns_server = ipaddress.IPv4Interface(net_config['Network']['Address']).ip.exploded

			net_config['Network']['IPMasquerade'] = "yes"
			net_config['DHCPServer']['DNS'] = dns_server

			save_configuration(PERSISTENT_TETHERING, mode)

		with open(NETWORK_CONFIG_FILE, "w") as net_file:
			net_config.write(net_file, space_around_delimiters = False)

		# when none requires to first write the current change before calling configure_lanserver
		if mode == "none":
			configure_lanserver(False, permanent = False)

	except (configparser.NoSectionError, configparser.NoOptionError) as ex:
		print("{}: error: missing section or option '{}' in {}".format(sys.argv[0], ex, NETWORK_CONFIG_FILE), file=sys.stderr)
	except ValueError as ex:
		print("{}: error: invalid configuration key: {}".format(sys.argv[0], ex), file=sys.stderr)
	except Exception as ex:
		print("{}: error: could not configure tethering mode to '{}': {}".format(sys.argv[0], ex, mode), file=sys.stderr)
	
	if restart_network:
		reload_iptables_rules()
		lib_network.restart_systemd_networkd()

def lanserver_enabled():
	"""
	Return a boolean indicating if the LAN server is enabled or not.
	"""

	enabled = None

	try:
		# Unfortunately, we must determine the LAN server state from the network configuration file because the dbus
		# interface of systemd-networkd is currently lacking methods to get informations about the state of the DHCP server.
		# This is not ideal because it supposes that the systemd-networkd is reloaded every time the configuration file
		# is modified.
		net_config = lib_system.systemd_configparser()
		with open(NETWORK_CONFIG_FILE, "r") as net_file:
			net_config.read_file(net_file)
			status = net_config['Network']['DHCPServer']

		enabled = status.lower() == "yes" or status.lower() == "true" or status.lower() == "on" or status == "1"
	except Exception as ex:
		print("{}: error: failed to read the LAN server configuration: {}".format(sys.argv[0], ex), file=sys.stderr)

	return enabled

def configure_lanserver(enable, permanent = True, restart_network = False):
	"""
	Enable or disable the LAN server (DHCP).

	Valid modes are (parameter "enable"):
	  * "True":  enable the LAN server
	  * "False": disable the LAN server

	Parameter @permanent is also a boolean that determine if the LAN server
	should be kept enabled when tethering is disabled (i.e. if LAN server has
	been manually enabled).

	Parameter @restart_network determine if systemd-networkd must be restarted
	once the configuration is modified. This allows to apply the new setup
	immediately. This is False by default to avoid restarting systemd-networkd
	multiple times when loading the configuration from the persistent partition.

	The LAN server is not disabled if tethering is enabled; it will remain active
	as long as tethering remains enabled.
	"""

	try:
		if permanent:
			if enable:
				save_configuration(PERSISTENT_LANSERVER)
			else:
				if os.path.exists(PERSISTENT_LANSERVER):
					os.remove(PERSISTENT_LANSERVER)

		net_config = lib_system.systemd_configparser()

		with open(NETWORK_CONFIG_FILE, "r") as net_file:
			net_config.read_file(net_file)

		if enable:
			net_config['Network']['DHCPServer'] = "yes"
			net_config['Network']['Address'] = "172.16.0.3/16"
			net_config["Network"]["LinkLocalAddressing"] = "no"
			net_config.remove_option('Network', 'DHCP')
			net_config.remove_option('Network', 'Gateway')
			net_config.remove_option('Network', 'DNS')
		else:
			if not os.path.exists(PERSISTENT_LANSERVER) and tethering_mode() == "none":
				net_config['Network']['DHCPServer'] = "no"
				net_config['Network']['DHCP'] = "ipv4"
				net_config["Network"]["LinkLocalAddressing"] = "yes"
				net_config.remove_option('Network', 'Address')

		with open(NETWORK_CONFIG_FILE, "w") as net_file:
			net_config.write(net_file, space_around_delimiters = False)
	except Exception as ex:
		print("{}: error: could not configure the LAN server: {}".format(sys.argv[0], ex), file=sys.stderr)

	if restart_network:
		reload_iptables_rules()
		lib_network.restart_systemd_networkd()

def load_configuration():
	"""
	Reload configuration saved on the persistent partition. This is needed as
	an update reverts all network configuration to the default state.

	The configuration loader is disable at the end of this function as the
	restored configuration will remain active until the next update and the
	configuration loader will be re-enabled automatically during this process.
	"""

	try:
		if os.path.exists(PERSISTENT_BRIDGED):
			with open(PERSISTENT_BRIDGED, "r") as config:
				interfaces = config.read().strip()

				# In case @interfaces is an empty string, re.split() returns [''] instead of []
				to_bridge = re.split("[ \t\n]", interfaces) if interfaces != "" else []

			configure_bridge(to_bridge)
		if os.path.exists(PERSISTENT_TETHERING):
			with open(PERSISTENT_TETHERING, "r") as config:
				mode = config.readline()

			configure_tethering(mode)
		if os.path.exists(PERSISTENT_LANSERVER):
			configure_lanserver(True)

		disable_configuration_loader()
	except Exception as ex:
		print("{}: error: failed to load configuration: {}".format(sys.argv[0], ex), file=sys.stderr)

if __name__ == '__main__':
	try:
		if sys.argv[1] == "get":
			if sys.argv[2] == "bridge":
				result = json.dumps(
					{ "bridge": bridged_interfaces() },
					indent = 4)
			elif sys.argv[2] == "tethering":
				result = json.dumps(
				    { "tethering": tethering_mode() },
					indent = 4)
			elif sys.argv[2] == "lanserver":
				result = json.dumps(
				    { "lanserver": "yes" if lanserver_enabled() else "no" },
					indent = 4)
			else:
				usage()

			print(result)
		elif sys.argv[1] == "set":
			if sys.argv[2] == "bridge":
				if_list = sys.argv[3:]
				configure_bridge(if_list, restart_network = True)
			elif sys.argv[2] == "tethering":
				configure_tethering(sys.argv[3], restart_network = True)
			elif sys.argv[2] == "lanserver":
				configure_lanserver(sys.argv[3] == "yes", restart_network = True)
			else:
				usage()
		elif sys.argv[1] == "load":
			if sys.argv[2] == "configuration" or sys.argv[2] == "config":
				load_configuration()
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
