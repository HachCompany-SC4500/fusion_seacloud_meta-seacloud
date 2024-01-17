#!/usr/bin/python3

import os.path
import os
import sys
import time
import subprocess
import lib_wifi
import lib_network

import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

def __logInfo(info):
	""" Generic function to log wifi connection information into an history file (CSV format).
	"wlan0" interface should be up.
	"""
	date_format = '%Y/%m/%d %H:%M:%S'
	try:
		# log stat code with a timestamp
		date = datetime.now()
		date_str = date.strftime(date_format)
		utc_date = datetime.utcnow()
		utc_date_str = utc_date.strftime(date_format)
		#line formatted for CSV file (';' as delimiter)
		timezone = time.tzname[1] if time.localtime( ).tm_isdst==1 else time.tzname[0]
		line = '{};{};{};{}'.format(timezone, date_str, utc_date_str, info)
		logger.info(line)
		print("\"%s\" added to Wifi CSV stats" % (line))
		return True
	except:
		pass
	return False

def __collectInfo():
	# iw dev wlan0 link
	try:
		output = subprocess.check_output(["iw", "dev", "wlan0", "link"])
		info = output.decode('utf-8')
		info = info.replace('\n',';')
		# Check internet access trying to contact any of the default servers [ 'storefsngeneral.blob.core.windows.net', 'pool.ntp.org' ]
		if lib_network.contact_server(interface_name="wlan0"):
			info = info + " Internet access: YES;"
		else:
			info = info + " Internet access: NO;"
		return info
	except subprocess.CalledProcessError as e:
		if e.returncode == 237:
			return "No WiFi dongle"
		print("Error while calling 'iw' commande: '%s'" % (e))
	except Exception as e:
		print("Generic exception while collecting info: %s" % (e))
	return "NA"

if __name__ == '__main__':
	"""This Python script aims at logging WiFi connection information into an history file (CSV format).
	This CSV file is used for stats extraction & computation by a dedicated Excel tool

	An optional command line argument "diagonly" is supported. In this case, this program displays the current connection information but does not log to file
	"""

	stats_file_path = "/media/persistent/system/wifi_stats.csv"

	# this program can receive one optional argument
	diagnostic_only = False
	if len(sys.argv) > 1:
		# diagonly option: In this case, this program displays the current connection information but does not log to file
		if sys.argv[1] == "diagonly":
			diagnostic_only = True
		else:
			print("")
			print("bad argument")
			print("")
			print("use: \"%s diagonly\" to display WiFi connection information, without log to csv file" % (sys.argv[0]))
			print("")
			print("use: \"%s\" to display WiFi connection information and to log it to csv file \"%s\"" % (sys.argv[0], stats_file_path))
			print("")
			exit(1)

	""" Create and configure a rotating logger to log all stats.
	Stats are logged in stats_file_path. When file the size is about to be exceeded, the file is closed and a new file is silently opened.
	The system will save old log files by appending the extensions .1
	"""
	# A do-nothing fallback handler used in case of exception creating a RotatingFileHandler
	class NullHandler(logging.Handler):
		def emit(self, record):
			pass

	logger = logging.getLogger('wifi_stats_logger')
	logger.setLevel(logging.INFO)

	# Check the wifi status and log only if wifi is configured and enabled
	wifi_manager = lib_wifi.WiFiManager(logger)
	wifi_status, message = wifi_manager.get_wifi_enabled_status()
	if wifi_status == "enabled":
		registered_service = ()
		success, message, registered_service = wifi_manager.get_registered_service()
		if success and len(registered_service) is not 0:
			try:
				# current log file is maximum 512Ko.
				# backup log file is 512Ko
				handler = RotatingFileHandler(stats_file_path, maxBytes=512*1024, backupCount=1)
			except:
				handler = NullHandler()
			logger.addHandler(handler)

			# Add log header if the file is missing or empty
			new_log_file = (not os.path.isfile(stats_file_path) or os.path.getsize(stats_file_path) == 0)
			if (new_log_file):
					logger.info("Time zone;Local time;UTC time;WiFi Info")

			# collect WiFi connect info here
			info = __collectInfo()

			print(info)

			if (diagnostic_only):
				exit(0)

			# log WiFi connect info here
			__logInfo(info)

		exit(0)
