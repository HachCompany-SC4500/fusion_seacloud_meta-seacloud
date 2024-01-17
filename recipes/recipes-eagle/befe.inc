##########
# WARNING: this file will be overwritten automatically by packager/build_image_components.sh script to get the revision from the current BEFE sources extracted into stuff folder by the packager
##########

SRC_URI = "git://git@stash.waterqualitytools.com:7999/fcfw/fusion_eagle_befe.git;protocol=ssh;branch=${SRCBRANCH}"

PV = "0.0.1"
SRCREV = "${AUTOREV}"
SRCBRANCH = "master"

