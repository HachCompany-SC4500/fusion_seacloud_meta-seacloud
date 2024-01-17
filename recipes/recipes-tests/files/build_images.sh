#!/bin/bash

#
# This script is used to generate artifacts used during tests
# This is not generated during build because mkfs.exfat and mkfs.ntfs are not available as native recipe to be used during this reicpe
# 

set -o errexit

function create_compressed_image() {
# $1 : build command
# $2 : file system name
    image="$2.img"
    archive="$image.tar.gz"
    echo "Create $archive with $1"
    dd if=/dev/zero bs=1M count=5 of="./$image"
    $1 "$image"
    tar -czf "$archive" "$image"
    rm "$image"
    echo "$archive created."
    echo
}

echo "Create test file system compressed images"
create_compressed_image "mkfs.ext2" "ext2"
create_compressed_image "mkfs.ext3" "ext3"
create_compressed_image "mkfs.ext4" "ext4"
create_compressed_image "mkfs.fat -F12" "fat12"
create_compressed_image "mkfs.fat -F16" "fat16"
create_compressed_image "mkfs.fat -F32" "fat32"
create_compressed_image "mkfs.exfat" "exfat"
create_compressed_image "mkfs.ntfs -F" "ntfs"

echo "All images have been properly been generated"
