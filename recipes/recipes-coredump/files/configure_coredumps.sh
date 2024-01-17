#!/bin/sh

# This script configures coredump file generation.
# If the controller is not in development mode it is disabled,
# otherwise it is enabled and the script sets the pattern and file location,

if [ -f "/media/persistent/development" ]; then
	mkdir -p /core_dumps
	sysctl -w kernel.core_pattern="/core_dumps/core"
	sysctl -w kernel.core_uses_pid=1
else
	# Disable coredumps
	sysctl -w kernel.core_pattern=""
	sysctl -w kernel.core_uses_pid=0
fi
