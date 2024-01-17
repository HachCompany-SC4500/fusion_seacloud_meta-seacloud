#!/usr/bin/env bash
#
# Copyright (C) 2020 Hach
# Author: Dragan Cecavac <dcecavac@witekio.com>
#

set -e

function check_mounted() {
	if grep -qs '/media/persistent ' /proc/mounts; then
		echo "/media/persistent is already mounted"
		exit 0
	fi
}

function ensure_bank_stability() {
	bank_stable="$(fw_printenv -n bank_stable)"

	if [ "${bank_stable}" = "false" ]; then
		echo "Bank not in stable state"
		exit 0
	fi
}

function fetch_key_fragment() {
	# Get the fuse device path to read its value.
	fragment="/sys/fsl_otp/HW_OCOTP_$1"
	# Strip leading spaces and tabs around (left and right) the read value.
	key_fragment="$(sed -e 's/^[ \t]*//g;s/[ \t]*$//g' "${fragment}")"
	# Format the previously read value to so that it’s an exactly 8-digit hexadecimal
	# value (left-leading "0" are kept). Example of output: "deadbeef".
	# If a failure occured reading the fuse value, we get an empty string. In this case,
	# we keep it empty to avoid entering the loop (printf emits a warning, but still
	# interpret the empty string as "0", and therefore converts it to "00000000").
	[ -n "${key_fragment}" ] && key_fragment="$(printf "%08x" "0x${key_fragment#0x}")" || key_fragment=""

	while [ -n "${key_fragment}" ] && [ "${key_fragment}" = "00000000" ]; do
		# Generate random non-zero 32-bit key fragment
		key_fragment_file="$(mktemp)"
		dd if=/dev/urandom of="${key_fragment_file}" bs=4 count=1
		key_fragment="$(hexdump -v "${key_fragment_file}" | head -n 1 | awk '{print $2$3}')"
		rm -- "${key_fragment_file}"

		# Burn the key fragment to the corresponding general purpose fuse
		if [ "${key_fragment}" != "00000000" ]
		then
			echo "${key_fragment}" > "${fragment}"
		fi

		# Reread the fuse after it has been flashed to handle formatting differences between
		# what is written and what is later read (e.g. leading zeros from written values may
		# be omitted when the fuse value is later read; "0b17" could be later read as "b17")
		key_fragment="$(sed -e 's/^[ \t]*//g;s/[ \t]*$//g' "${fragment}")"
		[ -n "${key_fragment}" ] && key_fragment="$(printf "%08x" "0x${key_fragment#0x}")" || key_fragment=""
	done

	# Build the key using the key fragments
	key="${key}${key_fragment}"
}

function fetch_encryption_key() {
	key=""

	fetch_key_fragment "GP10"
	fetch_key_fragment "GP11"
	fetch_key_fragment "GP20"
	fetch_key_fragment "GP21"

	key_file="$(mktemp)"
	echo "${key}" > "${key_file}"
}

function mmcblk0boot0_lock() {
	echo 1 > /sys/block/mmcblk0boot0/force_ro
}

function mmcblk0boot0_unlock() {
	echo 0 > /sys/block/mmcblk0boot0/force_ro
}

function prepare_pp_hooks() {
	# Remove old links if present
	rm -f /dev/mmcblk_active_pp
	rm -f /dev/mmcblk_hook_pp

	cmdline="$(cat /proc/cmdline)"
	if [[ ${cmdline} == *root=/dev/mmcblk0p2* ]]; then
		ln -s /dev/mmcblk0p5 /dev/mmcblk_active_pp
		ln -s /dev/mmcblk0p6 /dev/mmcblk_hook_pp
	elif [[ ${cmdline} == *root=/dev/mmcblk0p4* ]]; then
		ln -s /dev/mmcblk0p5 /dev/mmcblk_hook_pp
		ln -s /dev/mmcblk0p6 /dev/mmcblk_active_pp
	fi
}

function encrypt_pp() {
	# Backup the curent state of the persistent partition
	backup_dir="$(mktemp -d)"
	mkdir -p /media/persistent
	mount /dev/mmcblk_active_pp /media/persistent
	cp -a /media/persistent/. "${backup_dir}"
	umount /dev/mmcblk_active_pp

	# Encrypt and format the persistent partition
	fetch_encryption_key
	cryptsetup -qd "${key_file}" luksFormat /dev/mmcblk_active_pp
	cryptsetup -d "${key_file}" luksOpen /dev/mmcblk_active_pp persistent
	delete_encryption_key_file
	mkfs.ext4 -j /dev/mapper/persistent

	# Restore backed up files
	mount /dev/mapper/persistent /media/persistent
	cp -a "${backup_dir}/." /media/persistent
	umount /media/persistent

	cryptsetup luksClose /dev/mapper/persistent

	# At this point the persistent partition on the other partition bank
	# is still unencrypted. The simplest way to protect it is to overwrite
	# it with the encrypted one.
	dd if=/dev/mmcblk_active_pp of=/dev/mmcblk_hook_pp
	sync
}

function ensure_encryption() {
	pp_fstype="$(lsblk -f /dev/mmcblk_active_pp | tail -n 1 | cut -d ' ' -f2)"

	if [ "${pp_fstype}" = "ext4" ]; then
		encrypt_pp
	fi

	pp_fstype="$(lsblk -f /dev/mmcblk_active_pp | tail -n 1 | cut -d ' ' -f2)"

	if [[ ${pp_fstype} != crypt* ]]; then
		echo "/dev/mmcblk_active_pp has a wrong file system: ${pp_fstype}. cryptoLUKS was expected."
		exit -1
	fi
}

# Mount one of the persistent partitions
#
# $1 - mounting point
# $2 - partition name
# $3 - link to the partition block device
function mount_pp() {
	mounting_point="$1"
	partition_name="$2"
	device="$3"
	mkdir -p "$mounting_point"

	fetch_encryption_key
	cryptsetup -d "${key_file}" luksOpen "$device" "$partition_name"
	delete_encryption_key_file
	mount "/dev/mapper/$partition_name" "$mounting_point"
}

function mount_active_pp() {
	mount_pp "/media/persistent" "persistent" "/dev/mmcblk_active_pp"

	mkdir -p /mnt/fcc
	if [ -d /media/persistent/fcc ]; then
		mount --bind /media/persistent/fcc /mnt/fcc
	fi
}

function mount_passive_pp() {
	mount_pp "/media/passivePersistentPartition" "passivePersistentPartition" "/dev/mmcblk_hook_pp"
}

# Umount passive appfs
function unmount_passive_pp() {
	mounting_point="/media/passivePersistentPartition"
	device_name="passivePersistentPartition"

	if grep -qs "$mounting_point " /proc/mounts; then
		umount "$mounting_point"
	fi

	if [ -e "/dev/mapper/$device_name" ]; then
		cryptsetup luksClose "/dev/mapper/$device_name"
	fi
}

function delete_encryption_key_file() {
	# Remove temp key file
	rm -- "${key_file}"
}
