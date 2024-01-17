#!/usr/bin/env bash
#
# Copyright (C) 2020 Hach
# Author: Dragan Cecavac <dcecavac@witekio.com>
#
# Mount both persistent partitions.

# First try to source persistent-core.sh from /tmp/ in order to source the one
# embedded in a SWUpdate image when a update is running.
# When no update is running, the current persistent-core.sh located under /etc/ is used
if [ -f /tmp/persistent-core.sh ]; then
	source /tmp/persistent-core.sh
else
	source /etc/persistent-core.sh
fi

if ! grep -qs '/media/persistent ' /proc/mounts; then
	mount_active_pp
fi
if ! grep -qs '/media/passivePersistentPartition ' /proc/mounts; then
	mount_passive_pp
fi

