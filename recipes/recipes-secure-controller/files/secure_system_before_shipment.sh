#!/bin/sh

set -e

DEVELOPMENT_FILE_FLAG="/media/persistent/development"

# If not run as root, run the script again with elevated priviledges with the
# help of sudo (any user is allowed to run this script with root priviledges)
if [ "$(id -u)" != "0" ]
then
    sudo "$0"
    exit 0
fi

# Remove the file that act as a flag to enable development mode.
# As this file is removed, direct system access will be locked on during next
# boot, before any user interaction with the system is possible.
rm -f "${DEVELOPMENT_FILE_FLAG}"

# Lock the bootloader console access.
# This is to prevent system alteration through the bootloader. For example, one
# could remove the system security scripts from the bootloader console in order
# to keep the system unlocked.
/usr/local/bin/uboot_shell_control.sh lock
