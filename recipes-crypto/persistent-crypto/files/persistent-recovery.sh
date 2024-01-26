#!/usr/bin/env bash
#
# Copyright (C) 2020 Hach
# Author: Dragan Cecavac <dcecavac>
#

source /tmp/persistent-core.sh
source /tmp/swupdate-log.sh

function recovery_procedure()
{
	buffered_log "${0}: recovery_procedure(): checking the passive persistent partition filesystem type"
	pp_fstype="$(lsblk -f /dev/mmcblk_hook_pp | tail -n 1 | cut -d ' ' -f2)"

	if [[ ${pp_fstype} == crypt* ]]; then
		# If it uses the expected file system, copy it's data to the active persistent partitions
		buffered_log "${0}: recovery_procedure(): the passive persistent partition is encrypted, restoring the active one with the passive partition"
		dd if=/dev/mmcblk_hook_pp of=/dev/mmcblk_active_pp
		sync

		# There is no guarantee that even the other partition was not corrupted,
		# so "set +e" is used that we could try a different approach
		buffered_log "${0}: recovery_procedure(): trying to read the restored partition"
		set +e
		mount_active_pp
		set -e

		if grep -qs '/media/persistent ' /proc/mounts; then
			# Successfully recovered the secondary partition
			buffered_log "${0}: recovery_procedure(): the persistent partition has been successfully restored"
			exit 0
		else
			buffered_log "${0}: recovery_procedure(): the persistent partition recovery has failed"
			set +e
			# It's possible that the passive persistent partition's encryption is valid,
			# but that its file system is still corrupted.
			# In these cases luksOpen call from mount_active_pp() would be successful,
			# and therefore it is necessary to attempt a luksClose action and free up
			# the partition device for further usage.
			#
			# It would be possible to format the encrypted file system at this point,
			# but there would be nothing to recover and no real benefit.
			# That would further complicate the recovery mechanism, so it's better to fall through and
			# do a few unneeded steps before reformatting it.
			# This is an unusual edge case which is difficult to reproduce.
			cryptsetup luksClose /dev/mapper/persistent
			set -e
		fi
	fi

	set -e
	# If not mounted at this stage, it means that both persistent partitions are corrupted
	# so the only thing left to do is to format it
	buffered_log "${0}: recovery_procedure(): formatting the persistent partition"
	mkfs.ext4 -F /dev/mmcblk_active_pp
	buffered_log "${0}: recovery_procedure(): creating a new encrypted container"
	ensure_encryption
	buffered_log "${0}: recovery_procedure(): mounting the newly created persistent partition"
	mount_active_pp
	# copy init persistent partition
	tar -xf /tmp/persistent_init.tar.xz -C /media/persistent
}

check_mounted
ensure_bank_stability
prepare_pp_hooks
recovery_procedure
