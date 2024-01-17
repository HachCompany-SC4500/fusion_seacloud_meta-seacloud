#!/bin/sh
#
# This script ensures that persistent partition and root file system don't get overfilled, due to sensor logs and core dump files.
# Persistent partition is "/media/persistent/"
# Root file system is "/"
#
# For persistent partition, this is achieved by deleting log files one by one until a certain threshold is reached.
# For root file system, this is achieved by deleting core dump files one by one until a certain threshold is reached.
#
# It's important to point out that if there is an overflow caused by files in other different locations
# (not "/media/persistent/fcc/log/" neither "/core_dumps/"),this script will not provide the desired functionality and should be adjusted.
#
# Usage: garbage-collector.sh <instance_name>
# Where: <instance_name> is the name of the instance for the instantiated service garbage_collector@.service.
#        It can be "timer", "core" or "logs"


function get_usage()
{
	# This function returns the percentage usage of the folder received as argument
	usage=`df $1 | grep -o '[0-9]\+%' | sed 's/%//'`
}


function clean_folder()
{
	folder_to_monitor="$1"
	folder_to_clean="$2"
	allowed_usage="85"
	if [ -d "$folder_to_monitor" ] && [ -d "$folder_to_clean" ]; then
		get_usage $folder_to_monitor
		if [ "$usage" -gt "$allowed_usage" ]; then
			files_to_clean=($(ls -rt $folder_to_clean))
			for i in "${files_to_clean[@]}"
			do
				file_to_remove="$folder_to_clean/$i"
				rm "$file_to_remove"
				get_usage $folder_to_monitor
				if [ "$usage" -le "$allowed_usage" ]; then
					break;
				fi
			done
		fi
	fi
}

if [ "$1" = "timer" ]; then
	clean_folder /media/persistent /media/persistent/fcc/log
	clean_folder / /core_dumps
elif [ "$1" = "core" ]; then
	clean_folder / /core_dumps
elif [ "$1" = "logs" ]; then
	clean_folder /media/persistent /media/persistent/fcc/log
fi
