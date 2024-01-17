#!/bin/sh

# This script calibrates touch screen to ensure the touchscreen remains functional.

# load the additional module required
modprobe cyttsp5_device_access
# disable messages in dmesg logs
echo 0 > /proc/sys/kernel/hung_task_timeout_secs
# "echo" to provides calibration parameters
echo "0,0" > /sys/kernel/debug/1-0024/mfg_test/calibrate
# "cat" to effectively proceed with calibration and report a success status
cat /sys/kernel/debug/1-0024/mfg_test/calibrate
