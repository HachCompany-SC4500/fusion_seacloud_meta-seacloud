#!/usr/bin/python3
import lib_cellular_stats
import logging
import sys

if __name__ == '__main__':

	# Redirect lib_cellular_stats messages to stdout
	logger = logging.getLogger('lib_cellular_stats')
	logger.addHandler(logging.StreamHandler(sys.stdout))
	logger.setLevel(logging.INFO)

	lib_cellular_stats.logModemDetection()
