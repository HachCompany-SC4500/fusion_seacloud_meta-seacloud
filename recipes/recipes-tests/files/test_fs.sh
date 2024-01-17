#!/bin/bash

IMG_FILE=$1

if [ -z ${IMG_FILE} ];
then
	echo "Missing image archive file as parameter"
	exit 1
fi

MOUNT_FOLDER=tmp_mnt
SHORT_FILENAME=short
LONG_FILENAME=this_is_a_long_file_name
UTF_FILENAME=Joyeux_Noël

function populate_image() {
	result=0
	echo "Extract compressed archive"
	tar xf "$1"
	result=$(( $result || $? ))
	
	image=$(basename "$1" .tar.gz)
	
	echo "Mount file system and create files"
	# Clean mount unit in case a previous one has failed
	systemctl reset-failed
	systemd-mount "$image" "${MOUNT_FOLDER}"
	result=$(( $result || $? ))
	touch "${MOUNT_FOLDER}/${SHORT_FILENAME}" "${MOUNT_FOLDER}/${LONG_FILENAME}" "${MOUNT_FOLDER}/${UTF_FILENAME}"
	result=$(( $result || $? ))
	systemd-umount "${MOUNT_FOLDER}"
	result=$(( $result || $? ))
	
	echo "Remount and list content"
	systemd-mount "$image" "${MOUNT_FOLDER}"
	result=$(( $result || $? ))
	ls_output=$(ls "${MOUNT_FOLDER}/${SHORT_FILENAME}" "${MOUNT_FOLDER}/${LONG_FILENAME}" "${MOUNT_FOLDER}/${UTF_FILENAME}")
	result=$(( $result || $? ))
	echo $ls_output | grep -q "${MOUNT_FOLDER}/${SHORT_FILENAME}"
	result=$(( $result || $? ))
	echo $ls_output | grep -q "${MOUNT_FOLDER}/${LONG_FILENAME}"
	result=$(( $result || $? ))
	echo $ls_output | grep -q "${MOUNT_FOLDER}/${UTF_FILENAME}"
	result=$(( $result || $? ))
	systemd-umount "${MOUNT_FOLDER}"
	result=$(( $result || $? ))
	rm "$image"
	result=$(( $result || $? ))
	return $result
}


echo "Create temporary mount folder"
mkdir -p "${MOUNT_FOLDER}"

echo "Test file system image '$IMG_FILE'"
populate_image "${IMG_FILE}"
result=$?

rm -rf "${MOUNT_FOLDER}"
exit $result


