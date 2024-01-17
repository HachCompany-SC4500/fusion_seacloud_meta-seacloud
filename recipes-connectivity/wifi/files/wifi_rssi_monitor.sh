#!/bin/sh

# this shellscript is started by wifi_rssi_monitor.service
# it is replacing the previous python file wifi_rssi_monitor.py
# python was too expensive on resources, we therefore had to convert it into a shellscript

# need to ensure to kill wifi worker after receiving signal
# this occurs when service was stop/killed following the launch of config_wifi.py
# it needs to have priority over connman/dbus call therefore, we ensure worker won't thread lock
function termination_signal_handler() {
    killall wifi_rssi_monitor_worker.py
    exit 0
}

# Assign termination signal handle for SIGINT(2) and SIGTERM(15)
trap 'termination_signal_handler' 2
trap 'termination_signal_handler' 15

# return 0 or 1(running) if wifi_rssi_monitor_worker.py is found
function is_worker_running() {
    ps aux | grep -v grep | grep -c wifi_rssi_monitor_worker.py
}

# check if WiFi is enable and if worker is not already running
# if both are true, run the wifi worker
function start_wifi_worker() {
    WIFI_STATE=$(eval "cat /var/lib/connman/settings | grep -A 2 WiFi | grep Enable")
    if [[ $WIFI_STATE == *"true"* ]]; then
        until is_worker_running | grep -m 1 "0"; do sleep 1; done
        wifi_rssi_monitor_worker.py
    fi
}

# inifite loop calling start wifi worker every 30s
while true; do start_wifi_worker & sleep 30; done