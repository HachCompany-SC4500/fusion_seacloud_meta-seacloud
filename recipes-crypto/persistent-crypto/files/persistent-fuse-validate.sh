#!/usr/bin/env bash
#
# Copyright (C) 2020 Hach
# Author: Dragan Cecavac <dcecavac@witekio.com>
#
# If the encryption key changed, this script will perform the transition to new format.

source /tmp/swupdate-log.sh

function legacy_fetch_key_fragment() {
	fragment="/sys/fsl_otp/HW_OCOTP_$1"
	key_fragment=`cat ${fragment}`
	raw_key_fragment=`echo ${key_fragment} | cut -dx -f2`
	current_encryption_key="${current_encryption_key}${raw_key_fragment}"
}

if [ -f /etc/persistent-core.sh ]; then
	current_encryption_key="$(source /etc/persistent-core.sh && fetch_encryption_key && cat "${key_file}" && rm -- "${key_file}")"
else
	legacy_fetch_key_fragment "GP10"
	legacy_fetch_key_fragment "GP11"
	legacy_fetch_key_fragment "GP20"
	legacy_fetch_key_fragment "GP21"
fi

# This line could potentially burn the fuses on the controller with unburned fuses.
# With the current setup, this should not be possible, because persistent-recovery.sh should be called
# in case of encryption related failures, and an eventual fuse burning would be done in that place.
swu_img_encryption_key="$(source /tmp/persistent-core.sh && fetch_encryption_key && cat "${key_file}" && rm -- "${key_file}")"

# If the kernel fails to read hardware fuses, emit a log and exit with a non-zero value
# to stop the ongoing update and report a failure to the user.
# In such a case, a reboot of the system usually renders the hardware fuses available again.
if [ -z "${current_encryption_key}" ] || [ -z "${swu_img_encryption_key}" ]
then
	buffered_log "${0}: failed to read hardware fuses, unable to get the encryption key"
	exit 1
fi

buffered_log "${0}: checking the persistent partition passphrase"
# If the encryption key changed.
if [ "$current_encryption_key" != "$swu_img_encryption_key" ]; then
	buffered_log "${0}: passphrase is wrong, rebuilding the persistent partition with the right one"
	# Back up active persistent partition contents.
	buffered_log "${0}: backing up data on the persistent partition"
	ap_backup_dir="$(mktemp -d)"
	cp -a /media/persistent/. "${ap_backup_dir}"
	# Unmount and format the partition.
	buffered_log "${0}: unmounting the persistent partition"
	/etc/swupdate-compatibility.sh
	buffered_log "${0}: formatting the persistent partition"
	mkfs.ext4 -F /dev/mmcblk_active_pp

	# Encrypt the partition with the new key.
	source /tmp/persistent-core.sh
	prepare_pp_hooks
	buffered_log "${0}: creating a new encrypted container"
	ensure_encryption
	buffered_log "${0}: mounting the newly created persistent partition"
	mount_active_pp

	# Restore its content.
	buffered_log "${0}: restoring the backed-up data on the new persistent partition"
	cp -a "${ap_backup_dir}/." /media/persistent
	rm -rf -- "$ap_backup_dir"
fi
